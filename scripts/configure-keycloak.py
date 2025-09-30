#!/usr/bin/env python3
"""
Automated Keycloak configuration script for MCP Joke Server
Configures realm, clients, users, and scopes via Keycloak Admin API
"""

import json
import time
import sys
import requests
from typing import Dict, Any

KEYCLOAK_URL = "http://localhost:8080"
ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin"


class KeycloakSetup:
    def __init__(self):
        self.base_url = KEYCLOAK_URL
        self.admin_user = ADMIN_USER
        self.admin_password = ADMIN_PASSWORD
        self.access_token = None

    def wait_for_keycloak(self, max_retries: int = 30):
        """Wait for Keycloak to be ready"""
        print("Waiting for Keycloak to be ready...")
        for i in range(max_retries):
            try:
                response = requests.get(f"{self.base_url}/realms/master")
                if response.status_code == 200:
                    print("✓ Keycloak is ready")
                    return True
            except requests.exceptions.ConnectionError:
                pass
            time.sleep(2)
        print("✗ Keycloak did not become ready in time")
        return False

    def get_admin_token(self) -> bool:
        """Get admin access token"""
        print("Getting admin access token...")
        url = f"{self.base_url}/realms/master/protocol/openid-connect/token"
        data = {
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": self.admin_user,
            "password": self.admin_password
        }

        try:
            response = requests.post(url, data=data)
            if response.status_code == 200:
                self.access_token = response.json()["access_token"]
                print("✓ Admin token obtained")
                return True
            else:
                print(f"✗ Failed to get admin token: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Error getting admin token: {e}")
            return False

    def create_realm(self) -> bool:
        """Create MCP realm"""
        print("Creating MCP realm...")

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        # Check if realm exists
        check_url = f"{self.base_url}/admin/realms/mcp"
        response = requests.get(check_url, headers=headers)
        if response.status_code == 200:
            print("  Realm 'mcp' already exists, skipping creation")
            return True

        # Create realm
        url = f"{self.base_url}/admin/realms"
        data = {
            "realm": "mcp",
            "enabled": True,
            "sslRequired": "external",
            "registrationAllowed": False,
            "loginWithEmailAllowed": True,
            "duplicateEmailsAllowed": False,
            "resetPasswordAllowed": True,
            "editUsernameAllowed": False,
            "bruteForceProtected": True
        }

        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 201:
            print("✓ Realm 'mcp' created")
            return True
        else:
            print(f"✗ Failed to create realm: {response.status_code} - {response.text}")
            return False

    def create_client_scope(self) -> bool:
        """Create tools:mom_jokes scope"""
        print("Creating client scope 'tools:mom_jokes'...")

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        # Check if scope exists
        check_url = f"{self.base_url}/admin/realms/mcp/client-scopes"
        response = requests.get(check_url, headers=headers)
        if response.status_code == 200:
            scopes = response.json()
            if any(scope["name"] == "tools:mom_jokes" for scope in scopes):
                print("  Scope 'tools:mom_jokes' already exists, skipping creation")
                return True

        # Create scope
        data = {
            "name": "tools:mom_jokes",
            "description": "Access to mom jokes tool",
            "protocol": "openid-connect",
            "attributes": {
                "include.in.token.scope": "true",
                "display.on.consent.screen": "true"
            }
        }

        response = requests.post(check_url, json=data, headers=headers)
        if response.status_code == 201:
            print("✓ Client scope 'tools:mom_jokes' created")
            return True
        else:
            print(f"✗ Failed to create scope: {response.status_code} - {response.text}")
            return False

    def create_server_client(self) -> bool:
        """Create mcp-joke-server client"""
        print("Creating client 'mcp-joke-server'...")

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        # Check if client exists
        check_url = f"{self.base_url}/admin/realms/mcp/clients"
        response = requests.get(check_url, headers=headers)
        if response.status_code == 200:
            clients = response.json()
            existing = next((c for c in clients if c["clientId"] == "mcp-joke-server"), None)
            if existing:
                print("  Client 'mcp-joke-server' already exists, skipping creation")
                return True

        # Create client
        data = {
            "clientId": "mcp-joke-server",
            "name": "MCP Joke Server",
            "description": "Resource server for MCP joke tools",
            "enabled": True,
            "protocol": "openid-connect",
            "publicClient": False,
            "serviceAccountsEnabled": True,
            "authorizationServicesEnabled": True,
            "redirectUris": ["http://localhost:*"],
            "webOrigins": ["http://localhost:8000"],
            "attributes": {
                "audience": "mcp-joke-server"
            }
        }

        response = requests.post(check_url, json=data, headers=headers)
        if response.status_code == 201:
            print("✓ Client 'mcp-joke-server' created")

            # Assign scope to client
            client_id = response.headers.get("Location", "").split("/")[-1]
            if client_id:
                self._assign_scope_to_client(client_id, "tools:mom_jokes")
            return True
        else:
            print(f"✗ Failed to create server client: {response.status_code} - {response.text}")
            return False

    def create_inspector_client(self) -> bool:
        """Create mcp-inspector client"""
        print("Creating client 'mcp-inspector'...")

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        # Check if client exists
        check_url = f"{self.base_url}/admin/realms/mcp/clients"
        response = requests.get(check_url, headers=headers)
        if response.status_code == 200:
            clients = response.json()
            existing = next((c for c in clients if c["clientId"] == "mcp-inspector"), None)
            if existing:
                print("  Client 'mcp-inspector' already exists, skipping creation")
                return True

        # Create client
        data = {
            "clientId": "mcp-inspector",
            "name": "MCP Inspector",
            "description": "MCP Inspector testing client",
            "enabled": True,
            "protocol": "openid-connect",
            "publicClient": True,
            "standardFlowEnabled": True,
            "directAccessGrantsEnabled": True,  # For testing with password grant
            "redirectUris": [
                "http://localhost:6274/*",
                "http://localhost:3000/*",
                "http://localhost:*"
            ],
            "webOrigins": [
                "http://localhost:6274",
                "http://localhost:3000",
                "http://localhost:8000"
            ]
        }

        response = requests.post(check_url, json=data, headers=headers)
        if response.status_code == 201:
            print("✓ Client 'mcp-inspector' created")

            # Assign scope to client
            client_id = response.headers.get("Location", "").split("/")[-1]
            if client_id:
                self._assign_scope_to_client(client_id, "tools:mom_jokes")
            return True
        else:
            print(f"✗ Failed to create inspector client: {response.status_code} - {response.text}")
            return False

    def _assign_scope_to_client(self, client_id: str, scope_name: str):
        """Assign scope to client"""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        # Get scope ID
        scopes_url = f"{self.base_url}/admin/realms/mcp/client-scopes"
        response = requests.get(scopes_url, headers=headers)
        if response.status_code == 200:
            scopes = response.json()
            scope = next((s for s in scopes if s["name"] == scope_name), None)
            if scope:
                # Add as optional scope
                url = f"{self.base_url}/admin/realms/mcp/clients/{client_id}/optional-client-scopes/{scope['id']}"
                requests.put(url, headers=headers)
                print(f"  ✓ Assigned scope '{scope_name}' to client")

    def create_test_user(self) -> bool:
        """Create test user"""
        print("Creating test user...")

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        # Check if user exists
        check_url = f"{self.base_url}/admin/realms/mcp/users"
        response = requests.get(check_url, headers=headers, params={"username": "testuser"})
        if response.status_code == 200:
            users = response.json()
            if users:
                print("  User 'testuser' already exists, skipping creation")
                return True

        # Create user
        data = {
            "username": "testuser",
            "email": "testuser@example.com",
            "emailVerified": True,
            "enabled": True,
            "firstName": "Test",
            "lastName": "User",
            "credentials": [{
                "type": "password",
                "value": "testpass",
                "temporary": False
            }]
        }

        response = requests.post(check_url, json=data, headers=headers)
        if response.status_code == 201:
            print("✓ User 'testuser' created with password 'testpass'")
            return True
        else:
            print(f"✗ Failed to create user: {response.status_code} - {response.text}")
            return False

    def run_setup(self):
        """Run complete setup"""
        print("\n" + "="*60)
        print("MCP Joke Server - Keycloak Configuration")
        print("="*60 + "\n")

        if not self.wait_for_keycloak():
            return False

        if not self.get_admin_token():
            return False

        steps = [
            self.create_realm,
            self.create_client_scope,
            self.create_server_client,
            self.create_inspector_client,
            self.create_test_user
        ]

        for step in steps:
            if not step():
                print("\n✗ Setup failed")
                return False

        print("\n" + "="*60)
        print("✓ Keycloak setup completed successfully!")
        print("="*60 + "\n")

        print("Test commands:")
        print("-" * 40)
        print("\n1. Get an access token:")
        print("""curl -X POST http://localhost:8080/realms/mcp/protocol/openid-connect/token \\
  -H 'Content-Type: application/x-www-form-urlencoded' \\
  -d 'grant_type=password&client_id=mcp-inspector&username=testuser&password=testpass&scope=tools:mom_jokes'
""")

        print("2. Call protected mom joke tool with token:")
        print("""curl -X POST http://localhost:8000/mcp \\
  -H 'Authorization: Bearer <ACCESS_TOKEN>' \\
  -H 'Content-Type: application/json' \\
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_mom_joke","arguments":{}}}'
""")

        print("\n3. Environment variables for the server:")
        print("export KEYCLOAK_URL=http://localhost:8080")
        print("export KEYCLOAK_REALM=mcp")
        print("export RESOURCE_SERVER_URL=http://localhost:8000")
        print("export ALLOW_AUTH_BYPASS=false")

        return True


if __name__ == "__main__":
    setup = KeycloakSetup()
    success = setup.run_setup()
    sys.exit(0 if success else 1)