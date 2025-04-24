from mcp.server.fastmcp import FastMCP
import time
import signal
import sys
import json
import requests  # Thêm thư viện requests để call API

# Token (lưu ở đây tạm, production nên dùng biến môi trường nhé)
AUTH_TOKEN = "Bearer eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJZejRWejVyc090NkN1ME9qY2NocmdzWWhtSFdBbnRNTnVRZFpJNW9IVDd3In0.eyJleHAiOjE3NDU0Mzk1OTYsImlhdCI6MTc0NTQwMzU5NiwianRpIjoiZGYyM2ExNDctNzg4ZC00YjRjLThlOTMtZWVlY2RkZTVjNTcxIiwiaXNzIjoiaHR0cHM6Ly9rZXljbG9hay4yeHguaW8vYXV0aC9yZWFsbXMveG9yIiwiYXVkIjoiYWNjb3VudCIsInN1YiI6ImNkMWMzMzY2LTc0ZGQtNDdhYi04NjcwLTE1NGFhZDQzY2MwNiIsInR5cCI6IkJlYXJlciIsImF6cCI6Im9kb28tc2VydmljZSIsInNlc3Npb25fc3RhdGUiOiI2ODQ5Zjg1Zi0yMjAwLTQzMmItOWYzNi1lNDY5MzQzODA1MTIiLCJhY3IiOiIxIiwiYWxsb3dlZC1vcmlnaW5zIjpbImh0dHBzOi8veG9yY2xvdWQuZGV2LXNwYWNlLmNsb3VkIiwiaHR0cHM6Ly9pYW0uZGV2LXNwYWNlLmNsb3VkIiwiaHR0cDovL2xvY2FsaG9zdDozMDAwIiwiaHR0cDovL2xvY2FsaG9zdDo1MTczIiwiaHR0cHM6Ly90ZXN0LW9kb28uc29uYnEuZGV2LXNwYWNlLmNsb3VkIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJkZWZhdWx0LXJvbGVzLXhvciIsIm9mZmxpbmVfYWNjZXNzIiwidW1hX2F1dGhvcml6YXRpb24iLCJ1bmkub3duZXIiXX0sInJlc291cmNlX2FjY2VzcyI6eyJhY2NvdW50Ijp7InJvbGVzIjpbIm1hbmFnZS1hY2NvdW50IiwibWFuYWdlLWFjY291bnQtbGlua3MiLCJ2aWV3LXByb2ZpbGUiXX19LCJzY29wZSI6InByb2ZpbGUgZW1haWwiLCJzaWQiOiI2ODQ5Zjg1Zi0yMjAwLTQzMmItOWYzNi1lNDY5MzQzODA1MTIiLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwibmFtZSI6IlRlc3QgT3duZXIiLCJjdXN0b21lcklkIjoiNDcyIiwicHJlZmVycmVkX3VzZXJuYW1lIjoidGVzdC1vd25lckB4LW9yLmNsb3VkIiwiZ2l2ZW5fbmFtZSI6IlRlc3QiLCJmYW1pbHlfbmFtZSI6Ik93bmVyIiwiZW1haWwiOiJ0ZXN0LW93bmVyQHgtb3IuY2xvdWQifQ.DrqbSmi76PIm2IhyMTEH6_NuM6curFJcUlbRPAkAQ8fr7fX7Uula_0csYuW3zA7ANymc9G7H5bg518_m81lOyl23hJaf4KDWXLyEM0_SiXSDgkPcHeEq1gyv27FoOHhw_tPHarstVBcz_bkoYZt9ogf5mf47HGuGCOeL1kvvl5UG1HJHtzuq3dUeKi-LE7XptbL6OYVWtlXMO8Pa_WXenqOH29no3MQjatAhVpnQofIXv6AUL7hgloGN1pa1cqfB_xmNoACSGM8EReyCEManR6b5IfZdesQyIu_PXhyixsv7qH1MrC7Vttm9Q1dLBjgJX7i__5XulHKrB7EME9unJQ"

# Graceful shutdown handler
def signal_handler(sig, frame):
    print("Shutting down server gracefully...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Create MCP server
mcp = FastMCP(
    name="count-r",
    host="127.0.0.1",
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

# Tool 2: Fetch VM list from external API
@mcp.tool()
def get_vm_list() -> dict:
    """Fetch a list of VM servers from external API."""
    try:
        url = "http://192.168.1.204:3007/severs"
        headers = {
            "Content-Type": "application/json",
            "Authorization": AUTH_TOKEN
        }

        response = requests.get(url, headers=headers)
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
            "error": f"API request failed: {str(e)}"
        }

# Start server
if __name__ == "__main__":
    try:
        print("Starting MCP server 'count-r' on 127.0.0.1:5000")
        # Use this approach to keep the server running
        mcp.run()
    except Exception as e:
        print(f"Error: {e}")
        # Sleep before exiting to give time for error logs
        time.sleep(5)