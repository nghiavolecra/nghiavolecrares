import socket
import threading
import json
import os
import transform
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

torrent_files = []

class TrackerRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Lấy đường dẫn từ yêu cầu GET
        path = urlparse(self.path).path
        #ip = get_local_ip()

        # Kiểm tra xem yêu cầu có phải là "/announce" hay không
        if path.startswith("/announce/upload"):
            # Trả về mã trạng thái 200 và thông báo "OK"
            parsed_url = urlparse(self.path)
            # Trích xuất tham số từ query
            query_params = parse_qs(parsed_url.query)
            # Lấy giá trị của tham số 'info_hash'
            info_hash = query_params.get('info_hash', [None])[0]
            # Kiểm tra xem info hash có tồn tại không
            self._update_seeder(query_params.get('port', [None])[0], info_hash, query_params.get('ip', [None])[0])
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"OK")
        elif path.startswith("/announce/download"):
            # Trả về mã trạng thái 200 và thông báo "OK"
            parsed_url = urlparse(self.path)
            # Trích xuất tham số từ query
            query_params = parse_qs(parsed_url.query)
            # Lấy giá trị của tham số 'info_hash'
            info_hash = query_params.get('info_hash', [None])[0]
            # Kiểm tra xem info hash có tồn tại không
            response = self.find_and_print_line("tracker_directory/seeder_info.txt", info_hash)
            if response:
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(response.encode())  # Gửi nội dung dòng đã tìm thấy
            else:
                # Trả về mã trạng thái 404 nếu không tìm thấy dòng
                self.send_response(404)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"Not Found")
        elif path.startswith("/get-list"):
            list = torrent_files
            list = json.dumps(list)
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(list.encode("utf-8"))
        else:
            # Nếu đường dẫn không hợp lệ, trả về mã trạng thái 404
            self.send_response(404)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"Not Found")
    def do_POST(self):
        path = urlparse(self.path).path
        if path.startswith("/send-torrent"):
            content_length = int(self.headers['Content-Length'])  # Độ dài dữ liệu từ client
            post_data = self.rfile.read(content_length)  # Đọc dữ liệu gửi từ client
            torrent_file = json.loads(post_data.decode('utf-8'))
            response = "Torrent file already existed" if any(item["file_name"] == torrent_file["file_name"] for item in torrent_files) else "Send torrent file successfully"
            if response == "Send torrent file successfully":
                torrent_files.append(torrent_file)
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(response.encode("utf-8"))
    def _update_seeder(self, port, info_hash, ip):
        try:
            seeder_info = f"{ip}:{port}"
            file_dir = "tracker_directory"
            file_name = "seeder_info.txt"
            file_path = os.path.join(file_dir, file_name)
            os.makedirs(file_dir, exist_ok=True)  # Tạo thư mục nếu chưa tồn tại
            seeder_line = f"{info_hash}: {seeder_info}\n"

            # Đọc nội dung hiện tại của file
            if os.path.isfile(file_path):  # Kiểm tra xem file đã tồn tại hay chưa
                with open(file_path, 'r') as file:
                    lines = file.readlines()
            else:
                lines = []

            # Kiểm tra xem seeder đã tồn tại trong file hay chưa
            seeder_exists = False
            for i, line in enumerate(lines):
                if info_hash in line:
                    # Seeder đã tồn tại, kiểm tra xem port đã tồn tại trong hàng hay chưa
                    seeder_ports = line.split(':')[1].strip().split(',')
                    if port in seeder_ports:
                        # Port đã tồn tại, không cần cập nhật
                        print(f"Port {port} already exists for {info_hash}. Skipping update.")
                        return
                    else:
                        # Port chưa tồn tại, cập nhật thông tin
                        seeder_exists = True
                        if line[-1] != '\n':
                            line += '\n'  # Đảm bảo dòng cuối cùng có ký tự xuống dòng
                        lines[i] = line.rstrip() + f", {seeder_info}\n"  # Thêm thông tin mới vào dòng hiện tại
                        break

            # Nếu seeder chưa tồn tại, thêm một dòng mới
            if not seeder_exists:
                lines.append(seeder_line)

            # Ghi lại toàn bộ nội dung vào file
            with open(file_path, 'w') as file:
                file.writelines(lines)

            print(f"Seeder information updated for {file_name}.")
        except Exception as e:
            print(f"Error updating seeder information: {e}")
    
    def find_and_print_line(self, file_path, target_string):
        with open(file_path, 'r') as file:
            for line in file:
                if target_string + ": " in line:
                    return line.split(": ", 1)[1]  # In ra phần sau của dòng chứa chuỗi
                    break
        return NULL

def get_local_ip(interface='Wi-Fi'):
    # Chạy lệnh ipconfig và lấy kết quả
    result = subprocess.run(['ipconfig'], capture_output=True, text=True)

    # Phân tích kết quả để tìm địa chỉ IP
    ip_pattern = r'IPv4 Address.*?: (\d+\.\d+\.\d+\.\d+)'

    # Nếu interface được chỉ định, lọc theo interface
    if interface:
        interface_pattern = re.escape(interface)
        interface_start = re.search(interface_pattern, result.stdout, re.IGNORECASE)
        if not interface_start:
            return None  # Giao diện không tìm thấy
        # Lấy phần văn bản sau tên giao diện
        output_after_interface = result.stdout[interface_start.end():]
        # Tìm địa chỉ IP chỉ trong phần này
        match = re.search(ip_pattern, output_after_interface)
    else:
        # Nếu không chỉ định interface, tìm địa chỉ IP đầu tiên
        match = re.search(ip_pattern, result.stdout)

    # Trả về địa chỉ IP nếu tìm thấy, nếu không trả về None
    if match:
        return match.group(1)
    else:
        return None

def start_tracker(port=8080):
    # Khởi tạo một máy chủ HTTP với cổng được chỉ định
    server_address = (get_local_ip(), port)
    httpd = HTTPServer(server_address, TrackerRequestHandler)
    print(f"Tracker server is running on {get_local_ip()}:{port}")

    # Bắt đầu lắng nghe yêu cầu
    httpd.serve_forever()

# Khởi động máy chủ tracker
start_tracker()
