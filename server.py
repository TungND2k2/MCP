from mcp.server.fastmcp import FastMCP
import time
import signal
import sys
import json
import requests
from typing import Dict, Any
import os
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Lưu trữ thông tin xác thực Keycloak (Production: Dùng biến môi trường)
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "odoo-service")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "MxdUfdN1ejBROyAdr3i5fus03TdfTpfv")
KEYCLOAK_USERNAME = os.getenv("KEYCLOAK_USERNAME", "test-owner@x-or.cloud")
KEYCLOAK_PASSWORD = os.getenv("KEYCLOAK_PASSWORD", "123zXc_-")
KEYCLOAK_TOKEN_URL = "https://keycloak.2xx.io/auth/realms/xor/protocol/openid-connect/token"

# Dữ liệu mẫu dự phòng (khi API thất bại)
cloud_data_fallback = {
    "flavors": [
        {"id": "flv-001", "name": "m1.small", "vcpus": 2, "ram": 4096, "disk": 40},
        {"id": "flv-002", "name": "m1.medium", "vcpus": 4, "ram": 8192, "disk": 80}
    ],
    "ports": [
        {"id": "port-001", "server_id": "srv-001", "ip_address": "192.168.1.10", "port_number": 80, "protocol": "TCP"},
        {"id": "port-002", "server_id": "srv-002", "ip_address": "192.168.1.11", "port_number": 3306, "protocol": "TCP"}
    ],
    "networks": [
        {"id": "net-001", "name": "private-net-1", "status": "ACTIVE"},
        {"id": "net-002", "name": "private-net-2", "status": "ACTIVE"}
    ],
    "images": [
        {"id": "img-001", "name": "ubuntu-20.04", "os": "Ubuntu", "version": "20.04 LTS"},
        {"id": "img-002", "name": "centos-7", "os": "CentOS", "version": "7.9"}
    ],
    "subnets": [
        {"id": "subnet-001", "network_id": "net-001", "cidr": "192.168.1.0/24", "gateway_ip": "192.168.1.1"},
        {"id": "subnet-002", "network_id": "net-002", "cidr": "192.168.2.0/24", "gateway_ip": "192.168.2.1"}
    ],
    "servers": [
        {"id": "srv-001", "name": "web-server-01", "status": "ACTIVE", "flavor_id": "flv-001", "image_id": "img-001", "network_id": "net-001"},
        {"id": "srv-002", "name": "db-server-01", "status": "ACTIVE", "flavor_id": "flv-002", "image_id": "img-002", "network_id": "net-001"}
    ]
}

# Lưu trữ token và thời gian hết hạn
token_info = {
    "access_token": None,
    "expires_at": 0
}

# Cấu hình retry cho requests
session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[502, 503, 504])
session.mount("http://", HTTPAdapter(max_retries=retries))
session.mount("https://", HTTPAdapter(max_retries=retries))

# Graceful shutdown handler
def signal_handler(sig, frame):
    print("Shutting down server gracefully...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Hàm phụ để lấy token từ Keycloak
def fetch_auth_token() -> str:
    """Lấy token từ Keycloak."""
    try:
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "client_id": KEYCLOAK_CLIENT_ID,
            "client_secret": KEYCLOAK_CLIENT_SECRET,
            "grant_type": "password",
            "username": KEYCLOAK_USERNAME,
            "password": KEYCLOAK_PASSWORD
        }

        response = session.post(KEYCLOAK_TOKEN_URL, headers=headers, data=data, timeout=10)
        response.raise_for_status()

        token_data = response.json()
        token_info["access_token"] = f"Bearer {token_data['access_token']}"
        token_info["expires_at"] = time.time() + token_data.get("expires_in", 3600) - 30  # Trừ 30s để an toàn

        return token_info["access_token"]
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to fetch token from Keycloak: {str(e)}")

# Hàm phụ để lấy token hợp lệ
def get_valid_token() -> str:
    """Lấy token hợp lệ, làm mới nếu hết hạn."""
    if token_info["access_token"] is None or time.time() >= token_info["expires_at"]:
        return fetch_auth_token()
    return token_info["access_token"]

# Create MCP server
mcp = FastMCP(
    name="count-r",
    host="0.0.0.0",  # Đổi từ "127.0.0.1" thành "0.0.0.0"
    port=5000,
    timeout=30
)

# Tool 1: Count number of 'r' in a word
@mcp.tool()
def count_r(word: str) -> dict:
    """Count the number of 'r' letters in a given word."""
    try:
        if not isinstance(word, str):
            raise ValueError("Input must be a string")
        
        result = word.lower().count("r")
        return {
            "jsonrpc": "2.0",
            "method": "count_r",
            "id": 1,
            "result": result
        }
    except ValueError as ve:
        return {
            "jsonrpc": "2.0",
            "method": "count_r",
            "id": 1,
            "error": {
                "message": f"Error: {str(ve)}"
            }
        }
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "method": "count_r",
            "id": 1,
            "error": f"Unexpected error: {str(e)}"
        }

# Tool 2: Fetch auth token from Keycloak
@mcp.tool()
def get_auth_token() -> Dict[str, Any]:
    """Fetch an authentication token from Keycloak."""
    try:
        token = fetch_auth_token()
        return {
            "jsonrpc": "2.0",
            "method": "get_auth_token",
            "id": 1,
            "result": {
                "access_token": token,
                "expires_at": token_info["expires_at"]
            }
        }
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "method": "get_auth_token",
            "id": 1,
            "error": f"Failed to get token: {str(e)}"
        }

# Tool 3: Fetch VM list from external API
@mcp.tool()
def get_vm_list() -> Dict[str, Any]:
    """Fetch a list of VM servers from external API."""
    try:
        url = "http://192.168.1.204:3007/servers"
        headers = {
            "Content-Type": "application/json",
            "Authorization": get_valid_token()
        }

        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        vm_data = response.json()

        return {
            "jsonrpc": "2.0",
            "method": "get_vm_list",
            "id": 1,
            "result": vm_data
        }
    except requests.exceptions.RequestException as e:
        return {
            "jsonrpc": "2.0",
            "method": "get_vm_list",
            "id": 1,
            "error": f"API request failed: {str(e)}",
            "result": cloud_data_fallback["servers"]
        }

# Tool 4: Fetch flavors from external API
@mcp.tool()
def get_flavors() -> Dict[str, Any]:
    """Fetch a list of flavors from external API."""
    try:
        url = "http://192.168.1.204:3007/flavors"
        headers = {
            "Content-Type": "application/json",
            "Authorization": get_valid_token()
        }

        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        flavor_data = response.json()

        return {
            "jsonrpc": "2.0",
            "method": "get_flavors",
            "id": 1,
            "result": flavor_data
        }
    except requests.exceptions.RequestException as e:
        return {
            "jsonrpc": "2.0",
            "method": "get_flavors",
            "id": 1,
            "error": f"API request failed: {str(e)}",
            "result": cloud_data_fallback["flavors"]
        }

# Tool 5: Fetch ports from external API
@mcp.tool()
def get_ports() -> Dict[str, Any]:
    """Fetch a list of ports from external API."""
    try:
        url = "http://192.168.1.204:3007/ports"
        headers = {
            "Content-Type": "application/json",
            "Authorization": get_valid_token()
        }

        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        port_data = response.json()

        return {
            "jsonrpc": "2.0",
            "method": "get_ports",
            "id": 1,
            "result": port_data
        }
    except requests.exceptions.RequestException as e:
        return {
            "jsonrpc": "2.0",
            "method": "get_ports",
            "id": 1,
            "error": f"API request failed: {str(e)}",
            "result": cloud_data_fallback["ports"]
        }

# Tool 6: Fetch networks from external API
@mcp.tool()
def get_networks() -> Dict[str, Any]:
    """Fetch a list of networks from external API."""
    try:
        url = "http://192.168.1.204:3007/networks"
        headers = {
            "Content-Type": "application/json",
            "Authorization": get_valid_token()
        }

        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        network_data = response.json()

        return {
            "jsonrpc": "2.0",
            "method": "get_networks",
            "id": 1,
            "result": network_data
        }
    except requests.exceptions.RequestException as e:
        return {
            "jsonrpc": "2.0",
            "method": "get_networks",
            "id": 1,
            "error": f"API request failed: {str(e)}",
            "result": cloud_data_fallback["networks"]
        }

# Tool 7: Fetch images from external API
@mcp.tool()
def get_images() -> Dict[str, Any]:
    """Fetch a list of images from external API."""
    try:
        url = "http://192.168.1.204:3007/images"
        headers = {
            "Content-Type": "application/json",
            "Authorization": get_valid_token()
        }

        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        image_data = response.json()

        return {
            "jsonrpc": "2.0",
            "method": "get_images",
            "id": 1,
            "result": image_data
        }
    except requests.exceptions.RequestException as e:
        return {
            "jsonrpc": "2.0",
            "method": "get_images",
            "id": 1,
            "error": f"API request failed: {str(e)}",
            "result": cloud_data_fallback["images"]
        }

# Tool 8: Fetch subnets from external API
@mcp.tool()
def get_subnets() -> Dict[str, Any]:
    """Fetch a list of subnets from external API."""
    try:
        url = "http://192.168.1.204:3007/subnets"
        headers = {
            "Content-Type": "application/json",
            "Authorization": get_valid_token()
        }

        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        subnet_data = response.json()

        return {
            "jsonrpc": "2.0",
            "method": "get_subnets",
            "id": 1,
            "result": subnet_data
        }
    except requests.exceptions.RequestException as e:
        return {
            "jsonrpc": "2.0",
            "method": "get_subnets",
            "id": 1,
            "error": f"API request failed: {str(e)}",
            "result": cloud_data_fallback["subnets"]
        }

@mcp.tool()
def get_volumes() -> Dict[str, Any]:
    """Fetch a list of volumes from external API."""
    try:
        url = "http://192.168.1.204:3007/volumes"
        headers = {
            "Content-Type": "application/json",
            "Authorization": get_valid_token()
        }

        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        volume_data = response.json()

        return {
            "jsonrpc": "2.0",
            "method": "get_volumes",
            "id": 1,
            "result": volume_data
        }
    except requests.exceptions.RequestException as e:
        return {
            "jsonrpc": "2.0",
            "method": "get_volumes",
            "id": 1,
            "error": f"API request failed: {str(e)}",
            "result": cloud_data_fallback["volumes"]
        }

# Tool 9: Create a new VM
@mcp.tool()
def create_vm(name: str, flavorId: str, projectId: str, type: str, imageId: str = None, volumeId: str = None, portId: str = None, networkId: str = None, description: str = None) -> Dict[str, Any]:
    """Create a new virtual machine (VM) using the specified flavor, image/volume, and network."""
    try:
        # Kiểm tra các trường bắt buộc
        if not all([name, flavorId, projectId, type]):
            raise ValueError("name, flavorId, projectId, and type are required")

        # Kiểm tra loại trừ: chỉ được cung cấp imageId hoặc volumeId
        if imageId and volumeId:
            raise ValueError("Only one of imageId or volumeId can be provided")
        if not imageId and not volumeId:
            raise ValueError("Either imageId or volumeId must be provided")

        # Kiểm tra loại trừ: chỉ được cung cấp portId hoặc networkId
        if portId and networkId:
            raise ValueError("Only one of portId or networkId can be provided")
        if not portId and not networkId:
            raise ValueError("Either portId or networkId must be provided")

        # Tạo body request
        body = {
            "name": name,
            "flavorId": flavorId,
            "projectId": projectId,
            "type": type
        }
        if imageId:
            body["imageId"] = imageId
        if volumeId:
            body["volumeId"] = volumeId
        if portId:
            body["portId"] = portId
        if networkId:
            body["networkId"] = networkId
        if description:
            body["description"] = description

        # Gọi API
        url = "http://192.168.1.204:3007/servers"
        headers = {
            "Content-Type": "application/json",
            "Authorization": get_valid_token(),
            "Accept": "application/json"
        }

        response = session.post(url, headers=headers, json=body, timeout=10)
        response.raise_for_status()

        vm_data = response.json()

        return {
            "jsonrpc": "2.0",
            "method": "create_vm",
            "id": 1,
            "result": vm_data
        }
    except ValueError as ve:
        return {
            "jsonrpc": "2.0",
            "method": "create_vm",
            "id": 1,
            "error": {
                "message": f"Invalid input: {str(ve)}",
                "code": 400
            }
        }
    except requests.exceptions.HTTPError as he:
        status_code = he.response.status_code
        error_msg = he.response.text
        error_codes = {
            400: "Bad Request: Invalid or missing data",
            403: "Forbidden: Insufficient permissions for this project",
            404: "Not Found: Flavor, image, volume, or network does not exist",
            409: "Conflict: Port is already in use"
        }
        return {
            "jsonrpc": "2.0",
            "method": "create_vm",
            "id": 1,
            "error": {
                "message": f"API request failed: {error_codes.get(status_code, 'Unknown error')} - {error_msg}",
                "code": status_code
            }
        }
    except requests.exceptions.RequestException as e:
        # Trả về dữ liệu mẫu dự phòng
        fallback_vm = {
            "id": f"srv-{name.lower().replace(' ', '-')}",
            "name": name,
            "status": "ACTIVE",
            "flavorId": flavorId,
            "projectId": projectId,
            "imageId": imageId,
            "volumeId": volumeId,
            "portId": portId,
            "networkId": networkId,
            "description": description,
            "type": type
        }
        return {
            "jsonrpc": "2.0",
            "method": "create_vm",
            "id": 1,
            "error": f"API request failed: {str(e)}",
            "result": fallback_vm
        }

# Start server
if __name__ == "__main__":
    try:
        print("Starting MCP server 'count-r' on 127.0.0.1:5000")
        mcp.run()
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(5)