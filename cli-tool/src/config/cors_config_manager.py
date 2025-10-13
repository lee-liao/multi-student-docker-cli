#!/usr/bin/env python3
"""
CORS Configuration Manager

Handles generation of CORS (Cross-Origin Resource Sharing) configurations
for different rendering scenarios (CSR/SSR) and container networking.
"""

import os
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from src.core.port_assignment import PortAssignment


@dataclass
class CorsConfig:
    """Configuration for CORS generation"""
    username: str
    project_name: str
    template_type: str
    port_assignment: PortAssignment
    has_common_project: bool
    frontend_port: int
    backend_port: int
    additional_ports: Optional[List[int]] = None
    custom_origins: Optional[List[str]] = None


class CorsConfigManager:
    """Manages CORS configuration generation for different scenarios"""
    
    def __init__(self):
        """Initialize CORS configuration manager"""
        pass
    
    def generate_cors_config(self, config: CorsConfig) -> Dict[str, Any]:
        """
        Generate complete CORS configuration for all scenarios
        
        Args:
            config: CORS configuration parameters
            
        Returns:
            Dictionary with CORS variables for template substitution
        """
        # Generate CORS origins for different scenarios
        csr_origins = self._generate_csr_origins(config)
        ssr_origins = self._generate_ssr_origins(config)
        development_origins = self._generate_development_origins(config)
        container_hostnames = self._generate_container_hostnames(config)
        
        return {
            # Client-Side Rendering (CSR) origins
            'CORS_ORIGINS_CSR': ','.join(csr_origins),
            'CORS_ORIGINS_CSR_LIST': csr_origins,
            
            # Server-Side Rendering (SSR) origins
            'CORS_ORIGINS_SSR': ','.join(ssr_origins),
            'CORS_ORIGINS_SSR_LIST': ssr_origins,
            
            # Development origins (includes common dev ports)
            'CORS_ORIGINS_DEV': ','.join(development_origins),
            'CORS_ORIGINS_DEV_LIST': development_origins,
            
            # Container hostnames for internal communication
            'CONTAINER_HOSTNAMES': container_hostnames,
            'CONTAINER_HOSTNAMES_LIST': list(container_hostnames.values()),
            
            # Individual service URLs
            'FRONTEND_URL_LOCALHOST': f'http://localhost:{config.frontend_port}',
            'BACKEND_URL_LOCALHOST': f'http://localhost:{config.backend_port}',
            'FRONTEND_URL_CONTAINER': container_hostnames.get('frontend', ''),
            'BACKEND_URL_CONTAINER': container_hostnames.get('backend', ''),
            
            # Port-specific variables
            'FRONTEND_PORT': config.frontend_port,
            'BACKEND_PORT': config.backend_port,
        }
    
    def _generate_csr_origins(self, config: CorsConfig) -> List[str]:
        """
        Generate CORS origins for Client-Side Rendering (CSR)
        
        CSR applications run in the browser and make API calls directly
        from localhost to the backend API.
        """
        origins = set()
        
        # Primary frontend origin
        origins.add(f'http://localhost:{config.frontend_port}')
        
        # Backend origin (for API documentation, health checks)
        origins.add(f'http://localhost:{config.backend_port}')
        
        # Common development ports for frontend frameworks
        common_dev_ports = [3000, 3001, 5173, 8080, 8081, 4200, 5000]
        for port in common_dev_ports:
            if port in config.port_assignment.all_ports:
                origins.add(f'http://localhost:{port}')
        
        # Additional ports if specified
        if config.additional_ports:
            for port in config.additional_ports:
                origins.add(f'http://localhost:{port}')
        
        # Custom origins if specified
        if config.custom_origins:
            origins.update(config.custom_origins)
        
        return sorted(list(origins))
    
    def _generate_ssr_origins(self, config: CorsConfig) -> List[str]:
        """
        Generate CORS origins for Server-Side Rendering (SSR)
        
        SSR applications need both localhost origins (for client-side hydration)
        and container hostnames (for server-side API calls during rendering).
        """
        origins = set()
        
        # Include all CSR origins
        origins.update(self._generate_csr_origins(config))
        
        # Add container hostnames for SSR
        container_hostnames = self._generate_container_hostnames(config)
        
        # Frontend container hostname (for SSR API calls)
        if 'frontend' in container_hostnames:
            frontend_hostname = container_hostnames['frontend']
            # Common SSR ports
            ssr_ports = [3000, 3001, 8080]
            for port in ssr_ports:
                origins.add(f'http://{frontend_hostname.split("://")[1].split(":")[0]}:{port}')
        
        # Backend container hostname
        if 'backend' in container_hostnames:
            origins.add(container_hostnames['backend'])
        
        # Worker service hostname (for agent projects)
        if config.template_type == 'agent' and 'worker' in container_hostnames:
            origins.add(container_hostnames['worker'])
        
        return sorted(list(origins))
    
    def _generate_development_origins(self, config: CorsConfig) -> List[str]:
        """
        Generate comprehensive CORS origins for development
        
        Includes all possible development scenarios and common ports.
        """
        origins = set()
        
        # Include SSR origins (which include CSR origins)
        origins.update(self._generate_ssr_origins(config))
        
        # Add all student's assigned ports as potential origins
        for port in config.port_assignment.all_ports:
            origins.add(f'http://localhost:{port}')
        
        # Common development tools and frameworks
        dev_tools_ports = [
            3000, 3001, 3002,  # React, Next.js
            4200, 4201,        # Angular
            5173, 5174,        # Vite
            8080, 8081, 8082,  # Various dev servers
            9000, 9001,        # Webpack dev server
            5000, 5001,        # Flask, various
        ]
        
        for port in dev_tools_ports:
            origins.add(f'http://localhost:{port}')
        
        # HTTPS variants for production-like testing
        origins.add(f'https://localhost:{config.frontend_port}')
        origins.add(f'https://localhost:{config.backend_port}')
        
        return sorted(list(origins))
    
    def _generate_container_hostnames(self, config: CorsConfig) -> Dict[str, str]:
        """
        Generate container hostnames for Docker internal networking
        
        These are used for SSR scenarios where containers need to
        communicate with each other using Docker's internal DNS.
        """
        hostnames = {}
        
        # Base container name pattern: {username}-{service}
        base_name = config.username
        
        if config.template_type == 'rag':
            hostnames.update({
                'frontend': f'http://{base_name}-rag-frontend:3000',
                'backend': f'http://{base_name}-rag-backend:8000',
            })
        elif config.template_type == 'agent':
            hostnames.update({
                'frontend': f'http://{base_name}-agent-frontend:3000',
                'backend': f'http://{base_name}-agent-backend:8000',
                'worker': f'http://{base_name}-agent-worker:8001',
            })
        elif config.template_type == 'common':
            # Common infrastructure services
            hostnames.update({
                'postgres': f'http://{base_name}-postgres:5432',
                'mongodb': f'http://{base_name}-mongodb:27017',
                'redis': f'http://{base_name}-redis:6379',
                'chromadb': f'http://{base_name}-chromadb:8000',
                'jaeger': f'http://{base_name}-jaeger:16686',
                'prometheus': f'http://{base_name}-prometheus:9090',
                'grafana': f'http://{base_name}-grafana:3000',
            })
        
        # Add shared infrastructure hostnames if using common project
        if config.has_common_project and config.template_type != 'common':
            hostnames.update({
                'postgres_shared': f'http://{base_name}-postgres:5432',
                'mongodb_shared': f'http://{base_name}-mongodb:27017',
                'redis_shared': f'http://{base_name}-redis:6379',
                'chromadb_shared': f'http://{base_name}-chromadb:8000',
            })
        
        return hostnames
    
    def generate_cors_documentation(self, config: CorsConfig) -> str:
        """
        Generate CORS configuration documentation
        
        Returns markdown documentation explaining CORS setup for the project.
        """
        cors_config = self.generate_cors_config(config)
        
        doc = f"""## CORS Configuration Guide

### Understanding CORS in {config.template_type.upper()} Applications

CORS (Cross-Origin Resource Sharing) is crucial for web applications where your frontend needs to communicate with your backend API across different ports or domains.

#### Your Project Configuration

**Frontend URL:** `{cors_config['FRONTEND_URL_LOCALHOST']}`
**Backend URL:** `{cors_config['BACKEND_URL_LOCALHOST']}`

### Client-Side Rendering (CSR) Configuration

For React, Vue, Angular, and other client-side frameworks:

```bash
# Backend .env configuration
CORS_ORIGINS={cors_config['CORS_ORIGINS_CSR']}
```

**CSR Origins Include:**
"""
        
        for origin in cors_config['CORS_ORIGINS_CSR_LIST']:
            doc += f"- `{origin}`\n"
        
        doc += f"""
### Server-Side Rendering (SSR) Configuration

For Next.js, Nuxt.js, SvelteKit, and other SSR frameworks:

```bash
# Backend .env configuration for SSR
CORS_ORIGINS={cors_config['CORS_ORIGINS_SSR']}
```

**SSR Origins Include:**
"""
        
        for origin in cors_config['CORS_ORIGINS_SSR_LIST']:
            doc += f"- `{origin}`\n"
        
        doc += f"""
**Why SSR needs different CORS:**
- **CSR**: Browser makes API calls directly from localhost
- **SSR**: Server makes API calls from container hostname during rendering

### Container Hostnames for Internal Communication

When services need to communicate within Docker:

"""
        
        for service, hostname in cors_config['CONTAINER_HOSTNAMES'].items():
            doc += f"- **{service.title()}**: `{hostname}`\n"
        
        doc += f"""
### Development Configuration

For comprehensive development support (includes all common dev ports):

```bash
# Development .env configuration
CORS_ORIGINS={cors_config['CORS_ORIGINS_DEV']}
```

### Common CORS Issues and Solutions

#### Issue: "CORS policy" error in browser console

**Solutions:**
1. **Exact origin matching:**
   ```bash
   # Make sure CORS_ORIGINS matches exactly (including http://)
   CORS_ORIGINS={cors_config['FRONTEND_URL_LOCALHOST']}  # ✅ Correct
   CORS_ORIGINS=localhost:{config.frontend_port}         # ❌ Missing protocol
   ```

2. **Multiple development ports:**
   ```bash
   # Support multiple development ports
   CORS_ORIGINS={cors_config['CORS_ORIGINS_CSR']}
   ```

#### Issue: SSR hydration errors

**Solutions:**
1. **Add container hostnames to CORS:**
   ```bash
   CORS_ORIGINS={cors_config['CORS_ORIGINS_SSR']}
   ```

2. **Check internal service URLs:**
   ```bash
   # Test internal connectivity
   docker-compose exec frontend curl {cors_config['BACKEND_URL_CONTAINER']}/health
   ```

### Testing CORS Configuration

```bash
# Test CORS headers
curl -H "Origin: {cors_config['FRONTEND_URL_LOCALHOST']}" \\
     -H "Access-Control-Request-Method: GET" \\
     -H "Access-Control-Request-Headers: Content-Type" \\
     -X OPTIONS {cors_config['BACKEND_URL_LOCALHOST']}/api/health

# Expected response should include:
# Access-Control-Allow-Origin: {cors_config['FRONTEND_URL_LOCALHOST']}
# Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
```

### Environment-Specific Configurations

#### Local Development
```bash
CORS_ORIGINS={cors_config['CORS_ORIGINS_CSR']}
```

#### Docker Development
```bash
CORS_ORIGINS={cors_config['CORS_ORIGINS_SSR']}
```

#### Production (adjust domains as needed)
```bash
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```
"""
        
        return doc
    
    def validate_cors_config(self, config: CorsConfig) -> List[str]:
        """
        Validate CORS configuration and return list of potential issues
        
        Args:
            config: CORS configuration to validate
            
        Returns:
            List of validation warnings/issues
        """
        issues = []
        
        # Check port assignments
        if config.frontend_port not in config.port_assignment.all_ports:
            issues.append(f"Frontend port {config.frontend_port} not in assigned port range")
        
        if config.backend_port not in config.port_assignment.all_ports:
            issues.append(f"Backend port {config.backend_port} not in assigned port range")
        
        # Check for port conflicts
        if config.frontend_port == config.backend_port:
            issues.append("Frontend and backend ports cannot be the same")
        
        # Check additional ports
        if config.additional_ports:
            for port in config.additional_ports:
                if port not in config.port_assignment.all_ports:
                    issues.append(f"Additional port {port} not in assigned port range")
        
        # Validate custom origins format
        if config.custom_origins:
            for origin in config.custom_origins:
                if not origin.startswith(('http://', 'https://')):
                    issues.append(f"Custom origin '{origin}' should include protocol (http:// or https://)")
        
        return issues


def create_cors_config(username: str, project_name: str, template_type: str,
                      port_assignment: PortAssignment, has_common_project: bool = False,
                      frontend_port: Optional[int] = None, backend_port: Optional[int] = None,
                      additional_ports: Optional[List[int]] = None,
                      custom_origins: Optional[List[str]] = None) -> CorsConfig:
    """
    Create CORS configuration with automatic port assignment
    
    Args:
        username: Student's username
        project_name: Name of the project
        template_type: Type of project (rag, agent, common)
        port_assignment: Student's port assignment
        has_common_project: Whether using shared infrastructure
        frontend_port: Frontend port (auto-assigned if None)
        backend_port: Backend port (auto-assigned if None)
        additional_ports: Additional ports to include in CORS
        custom_origins: Custom origins to include
        
    Returns:
        CorsConfig object
    """
    all_ports = port_assignment.all_ports
    
    # Auto-assign ports if not specified
    if frontend_port is None:
        # Frontend typically gets the 9th port (index 8)
        frontend_port = all_ports[8] if len(all_ports) > 8 else all_ports[-1]
    
    if backend_port is None:
        # Backend typically gets the 8th port (index 7)
        backend_port = all_ports[7] if len(all_ports) > 7 else all_ports[-2]
    
    return CorsConfig(
        username=username,
        project_name=project_name,
        template_type=template_type,
        port_assignment=port_assignment,
        has_common_project=has_common_project,
        frontend_port=frontend_port,
        backend_port=backend_port,
        additional_ports=additional_ports,
        custom_origins=custom_origins
    )


def generate_cors_variables(username: str, project_name: str, template_type: str,
                           port_assignment: PortAssignment, has_common_project: bool = False,
                           **kwargs) -> Dict[str, Any]:
    """
    Convenience function to generate CORS template variables
    
    Args:
        username: Student's username
        project_name: Name of the project
        template_type: Type of project (rag, agent, common)
        port_assignment: Student's port assignment
        has_common_project: Whether using shared infrastructure
        **kwargs: Additional arguments for create_cors_config
        
    Returns:
        Dictionary of CORS variables for template substitution
    """
    manager = CorsConfigManager()
    config = create_cors_config(
        username=username,
        project_name=project_name,
        template_type=template_type,
        port_assignment=port_assignment,
        has_common_project=has_common_project,
        **kwargs
    )
    
    return manager.generate_cors_config(config)