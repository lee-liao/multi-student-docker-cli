"""
Port Assignment Management

This module handles reading and parsing encrypted port assignment data
for the multi-student Docker Compose CLI tool.
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple, Dict
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend


@dataclass
class PortAssignment:
    """Represents a student's port assignment with flexible segments"""
    
    login_id: str
    segment1_start: int
    segment1_end: int
    segment2_start: Optional[int] = None
    segment2_end: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def segment1_range(self) -> range:
        """Get segment1 as a range object"""
        return range(self.segment1_start, self.segment1_end + 1)
    
    @property
    def segment2_range(self) -> Optional[range]:
        """Get segment2 as a range object (None if not assigned)"""
        if self.segment2_start is not None and self.segment2_end is not None:
            return range(self.segment2_start, self.segment2_end + 1)
        return None
    
    @property
    def all_ports(self) -> List[int]:
        """Get all assigned ports as a flat sorted list"""
        ports = list(self.segment1_range)
        if self.segment2_range:
            ports.extend(list(self.segment2_range))
        return sorted(ports)
    
    @property
    def total_ports(self) -> int:
        """Get total number of assigned ports"""
        count = len(self.segment1_range)
        if self.segment2_range:
            count += len(self.segment2_range)
        return count
    
    @property
    def has_two_segments(self) -> bool:
        """Check if this assignment has two segments"""
        return self.segment2_start is not None and self.segment2_end is not None
    
    @property
    def is_continuous(self) -> bool:
        """Check if all ports form a continuous range"""
        if not self.has_two_segments:
            return True  # Single segment is always continuous
        
        # Check if segment2 starts immediately after segment1 ends
        return self.segment2_start == self.segment1_end + 1
    
    def __str__(self) -> str:
        """String representation of port assignment"""
        segment1 = f"{self.segment1_start}-{self.segment1_end}"
        if self.has_two_segments:
            segment2 = f"{self.segment2_start}-{self.segment2_end}"
            return f"{self.login_id}: {segment1}, {segment2} ({self.total_ports} ports)"
        else:
            return f"{self.login_id}: {segment1} ({self.total_ports} ports)"


class PortAssignmentDecryptor:
    """Handles decryption of encrypted port assignment files"""
    
    # Must match the key used in encrypt_tool.py
    ENCRYPTION_KEY = b'multi_student_docker_compose_key_2024_secure_port_assignments'[:32]
    
    def __init__(self):
        self.backend = default_backend()
    
    def decrypt_data(self, encrypted_data: bytes) -> str:
        """Decrypt encrypted data back to string"""
        try:
            # Extract IV and encrypted content
            iv = encrypted_data[:16]
            encrypted_content = encrypted_data[16:]
            
            # Create cipher
            cipher = Cipher(algorithms.AES(self.ENCRYPTION_KEY), modes.CBC(iv), backend=self.backend)
            decryptor = cipher.decryptor()
            
            # Decrypt
            padded_data = decryptor.update(encrypted_content)
            padded_data += decryptor.finalize()
            
            # Remove padding
            unpadder = padding.PKCS7(128).unpadder()
            data = unpadder.update(padded_data)
            data += unpadder.finalize()
            
            return data.decode('utf-8')
            
        except Exception as e:
            raise ValueError(f"Failed to decrypt port assignment data: {e}")


class PortAssignmentManager:
    """Manages port assignments for students"""
    
    def __init__(self, encrypted_file_path: str = None):
        """
        Initialize port assignment manager
        
        Args:
            encrypted_file_path: Path to encrypted port assignment file.
                               If None, will auto-detect latest version.
        """
        self.encrypted_file_path = encrypted_file_path
        self.assignments: Dict[str, PortAssignment] = {}
        self.metadata: Dict = {}
        self._loaded = False
    
    def find_latest_encrypted_file(self, search_dir: str = ".") -> Optional[str]:
        """
        Find the latest version of encrypted port assignment file
        
        Args:
            search_dir: Directory to search for encrypted files
            
        Returns:
            Path to latest encrypted file or None if not found
        """
        import glob
        import re
        
        pattern = os.path.join(search_dir, "student-port-assignments-v*.enc")
        files = glob.glob(pattern)
        
        if not files:
            return None
        
        # Extract version numbers and sort
        version_files = []
        for file_path in files:
            filename = os.path.basename(file_path)
            match = re.search(r'v(\d+)\.(\d+)', filename)
            if match:
                major, minor = int(match.group(1)), int(match.group(2))
                version_files.append((major, minor, file_path))
        
        if not version_files:
            return None
        
        # Sort by version (highest first)
        version_files.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return version_files[0][2]
    
    def load_assignments(self) -> bool:
        """
        Load port assignments from encrypted file
        
        Returns:
            True if successful, False otherwise
        """
        if self._loaded:
            return True
        
        # Auto-detect encrypted file if not specified
        if not self.encrypted_file_path:
            self.encrypted_file_path = self.find_latest_encrypted_file()
            if not self.encrypted_file_path:
                raise FileNotFoundError(
                    "No encrypted port assignment file found. "
                    "Expected file like 'student-port-assignments-v1.0.enc'"
                )
        
        if not os.path.exists(self.encrypted_file_path):
            raise FileNotFoundError(f"Encrypted port assignment file not found: {self.encrypted_file_path}")
        
        try:
            # Read encrypted file
            with open(self.encrypted_file_path, 'rb') as f:
                encrypted_data = f.read()
            
            # Decrypt data
            decryptor = PortAssignmentDecryptor()
            decrypted_data = decryptor.decrypt_data(encrypted_data)
            
            # Parse JSON
            data = json.loads(decrypted_data)
            self.metadata = {
                'version': data.get('version'),
                'created_at': data.get('created_at'),
                'total_assignments': data.get('total_assignments')
            }
            
            # Parse assignments
            self.assignments = {}
            for assignment_data in data.get('assignments', []):
                assignment = PortAssignment(
                    login_id=assignment_data['login_id'],
                    segment1_start=assignment_data['segment1_start'],
                    segment1_end=assignment_data['segment1_end'],
                    segment2_start=assignment_data.get('segment2_start'),
                    segment2_end=assignment_data.get('segment2_end')
                )
                self.assignments[assignment.login_id] = assignment
            
            self._loaded = True
            return True
            
        except Exception as e:
            raise RuntimeError(f"Failed to load port assignments: {e}")
    
    def get_student_ports(self, login_id: str) -> Tuple[range, Optional[range]]:
        """
        Get port ranges for a student based on login ID
        
        Args:
            login_id: Student's login ID (case-sensitive)
            
        Returns:
            Tuple of (segment1_range, segment2_range_or_None)
            
        Raises:
            PermissionError: If login ID not found or unauthorized
        """
        if not self._loaded:
            self.load_assignments()
        
        # Linux login IDs are case-sensitive - use exact match
        if login_id in self.assignments:
            assignment = self.assignments[login_id]
            return assignment.segment1_range, assignment.segment2_range
        else:
            # Provide helpful error message for case sensitivity
            similar_ids = [uid for uid in self.assignments.keys() if uid.lower() == login_id.lower()]
            if similar_ids:
                raise PermissionError(
                    f"Login ID '{login_id}' not found. Did you mean '{similar_ids[0]}'? "
                    f"Note: Login IDs are case-sensitive."
                )
            else:
                raise PermissionError(f"Login ID '{login_id}' not authorized")
    
    def get_student_assignment(self, login_id: str) -> PortAssignment:
        """
        Get complete port assignment for a student
        
        Args:
            login_id: Student's login ID (case-sensitive)
            
        Returns:
            PortAssignment object
            
        Raises:
            PermissionError: If login ID not found or unauthorized
        """
        if not self._loaded:
            self.load_assignments()
        
        if login_id in self.assignments:
            return self.assignments[login_id]
        else:
            # Trigger the same error handling as get_student_ports
            self.get_student_ports(login_id)  # This will raise appropriate error
    
    def list_all_assignments(self) -> List[PortAssignment]:
        """
        Get list of all port assignments (for admin use)
        
        Returns:
            List of all PortAssignment objects
        """
        if not self._loaded:
            self.load_assignments()
        
        return list(self.assignments.values())
    
    def get_metadata(self) -> Dict:
        """
        Get metadata about the port assignment file
        
        Returns:
            Dictionary with version, created_at, total_assignments
        """
        if not self._loaded:
            self.load_assignments()
        
        return self.metadata.copy()
    
    def validate_port_in_range(self, login_id: str, port: int) -> bool:
        """
        Check if a port is within the student's assigned ranges
        
        Args:
            login_id: Student's login ID
            port: Port number to check
            
        Returns:
            True if port is in student's assigned ranges
        """
        try:
            assignment = self.get_student_assignment(login_id)
            return port in assignment.all_ports
        except PermissionError:
            return False


# Convenience function for getting current user's ports
def get_current_user_ports() -> Tuple[range, Optional[range]]:
    """
    Get port ranges for the current user (from $USER environment variable)
    
    Returns:
        Tuple of (segment1_range, segment2_range_or_None)
        
    Raises:
        PermissionError: If user not authorized
        RuntimeError: If port assignment file cannot be loaded
    """
    import os
    
    login_id = os.environ.get('USER')
    if not login_id:
        raise RuntimeError("Cannot determine current user. $USER environment variable not set.")
    
    manager = PortAssignmentManager()
    return manager.get_student_ports(login_id)


def get_current_user_assignment() -> PortAssignment:
    """
    Get complete port assignment for the current user
    
    Returns:
        PortAssignment object for current user
        
    Raises:
        PermissionError: If user not authorized
        RuntimeError: If port assignment file cannot be loaded
    """
    import os
    
    login_id = os.environ.get('USER')
    if not login_id:
        raise RuntimeError("Cannot determine current user. $USER environment variable not set.")
    
    manager = PortAssignmentManager()
    return manager.get_student_assignment(login_id)