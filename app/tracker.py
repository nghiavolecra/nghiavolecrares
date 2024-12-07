import socket
import threading
import json
import os
import convert
import sys
import hashlib
import os
import bencodepy
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import urllib.parse
import subprocess
from urllib.request import urlopen
import re as r

class TrackerRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Lấy đường dẫn từ yêu cầu GET
        path = urlparse(self.path).path
        ip = get_local_ip()

        # Kiểm tra xem yêu cầu có phải là "/p2p" hay không
        if path.startswith("/p2p/upload"):
            parsed_url = urlparse(self.path)
            # Trích xuất tham số từ query
            query_params = parse_qs(parsed_url.query)
            info_hash = query_params.get('info_hash', [None])[0]
            ip = query_params.get('ip', [None])[0]
            response_status_code = self._update_seeder(query_params.get('port', [None])[0], info_hash, ip)
            self.send_response(response_status_code)
            self.send_header('Content-type', 'text/html')
            self.end_headers()                        
            return
        elif path.startswith("/p2p/download"):
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)                       
            info_hash = query_params.get('info_hash', [None])[0]
            response = self.get_list_of_seeder("list_of_seeders/seeder_info.txt", info_hash)
            if response:
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(response.encode())  # Gửi nội dung dòng đã tìm thấy
            else:
                # Không tìm thấy
                self.send_response(404)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"Not Found")
        elif path.startswith("/p2p/disconnect"):
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            info_hash = query_params.get('info_hash', [None])[0]
            ip = query_params.get('ip', [None])[0]
            INFO_PATH = os.path.join("list_of_seeders","seeder_info.txt")
            status_code = self._disconnect_seeder(query_params.get('port', [None])[0], info_hash, ip)
            self.send_response(status_code)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            return
        else:
            # Đường dẫn không hợp lệ
            self.send_response(404)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"Not Found")

    def _update_seeder(self, port, info_hash, ip):
        try:
            seeder_info = f"{ip}:{port}"
            file_dir = "list_of_seeders"
            file_name = "seeder_info.txt"
            file_path = os.path.join(file_dir, file_name)
            os.makedirs(file_dir, exist_ok=True)  # Tạo thư mục nếu chưa tồn tại
            seeder_line = f"{info_hash}: {seeder_info}\n"

            if os.path.isfile(file_path):
                with open(file_path, 'r', encoding='utf-8') as file:
                    lines = file.readlines()
            else:
                lines = []

            seeder_exists = False
            for i, line in enumerate(lines):
                if info_hash in line:
                    seeder_ports = line.split(':')[1].strip().split(',')
                    print(f'Seeder port {seeder_ports}')
                    if ip in seeder_ports:
                        print(f"Port {port} already exists for {info_hash}. Skipping update.")
                        return 201
                    else:
                        seeder_exists = True
                        if line[-1] != '\n':
                            line += '\n'
                        lines[i] = line.rstrip() + f", {seeder_info}\n"
                        break

            if not seeder_exists:
                lines.append(seeder_line)

            with open(file_path, 'w', encoding='utf-8') as file:
                file.writelines(lines)

            print(f"Seeder information updated for {file_name}.")
            return 200
        except Exception as e:
            print(f"Error updating seeder information: {e}")

    def _disconnect_seeder(self, port, info_hash, ip):
        try:
            file_dir = "list_of_seeders"
            file_name = "seeder_info.txt"
            file_path = os.path.join(file_dir, file_name)

            if os.path.isfile(file_path):
                with open(file_path, 'r', encoding='utf-8') as file:
                    lines = file.readlines()
            else:
                lines = []
                return 201

            updated_lines = []
            target = f"{ip}:{port}"
            if lines == []: return 201

            for line in lines:
                if line.startswith(info_hash + ":"):
                    parts = line.strip().split(": ", 1)
                    if len(parts) == 2:
                        peers = parts[1].split(", ")
                        num_peers = len(peers)
                        peers = [peer for peer in peers if peer != target]
                        if peers:
                            updated_lines.append(f"{info_hash}: {', '.join(peers)}\n")
                            if (num_peers == len(peers)):
                                return 201
                        if(num_peers == 0):
                            return 201
                else:
                    updated_lines.append(line)
                    return 201

            with open(file_path, "w", encoding='utf-8') as file:
                file.writelines(updated_lines)

            print(f"Seeder information updated for client {ip}:{port}.")
            return 200
        except Exception as e:
            print(f"Error updating seeder information: {e}")

    def get_list_of_seeder(self, file_path, target_string):
        if not os.path.isfile(file_path):
            return None
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                if target_string + ": " in line:
                    return line.split(": ", 1)[1]
        return None

def get_local_ip():
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    return local_ip

def read_seeder_info(file_path):
    ip_port_list = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                _, ip_port = line.split(": ", 1)
                ip, port = ip_port.split(":")
                ip_port_list.append({"ip": ip, "port": int(port)})
            except ValueError:
                print(f"Invalid line format: {line}")
    return ip_port_list

def start_tracker(port=6880):
    server_address = (get_local_ip(), port)
    httpd = HTTPServer(server_address, TrackerRequestHandler)
    print(f"Tracker server is running on {get_local_ip()}:{port}")
    httpd.serve_forever()

start_tracker()
