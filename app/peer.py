import socket
import os
import bencodepy
import threading
import sys
import convert
import requests
import hashlib
import math
import subprocess
from urllib.request import urlopen
import re
import json
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk


class Peer:
    def __init__(self):
        self.listen_socket = None 
        self.port = None
        self.bytes = 0
        self.file_path = []
    
    def find_empty_port(self, start_port=6881, end_port=65535):
        for port in range(start_port, end_port + 1):
            try:
                # Thử bind socket đến cổng được chỉ định
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind((get_local_ip(), port))
                # Nếu không có ngoại lệ xảy ra, cổng này không được sử dụng
                return port
            except OSError:
                # Cổng đã được sử dụng, thử cổng tiếp theo
                continue
        # Không tìm thấy cổng trống trong phạm vi được chỉ định
        return None

    def write_string_to_file(self, string):
        file_name = f"info_{self.port}.txt"
        file_dir = "peer_file_path"
        file_path = os.path.join(file_dir, file_name)
        os.makedirs(file_dir, exist_ok=True)  # Tạo thư mục nếu chưa tồn tại
        # Đảm bảo chỉ ghi một chuỗi vào mỗi hàng
        unique_strings = set()

        # Đọc dữ liệu từ file để kiểm tra chuỗi trùng lặp
        try:
            with open(file_path, 'r') as file:
                for line in file:
                    unique_strings.add(line.strip())
        except FileNotFoundError:
            pass  # Bỏ qua lỗi nếu file không tồn tại

        # Thêm chuỗi mới vào tập hợp
        unique_strings.add(string)

        # Ghi các chuỗi vào file
        with open(file_path, 'w', encoding='utf-8') as file:
            for unique_string in unique_strings:
                file.write(unique_string + '\n')

    # def create_torrent_file(self, file_path, file_dir, tracker_url):
    #     file_name = os.path.basename(file_path)
    #     self.write_string_to_file(file_path)
    #     print(f"Creating torrent file for {file_name}...")
    #     info_hash = convert.create_torrent(file_path, tracker_url, os.path.join(file_dir, f'{file_name}.torrent'))
    def create_torrent_file(self, file_path, file_dir, tracker_url):
        file_name = os.path.basename(file_path)
        self.write_string_to_file(file_path)
        print(f"Creating torrent file for {file_name}...")
        info_hash = convert.create_torrent(file_path, tracker_url, os.path.join(file_dir, f'{file_name}.torrent'))
        return info_hash


    def upload_torrent_file(self, file_path, tracker_url):
        try:
            # Đọc dữ liệu từ file torrent
            with open(file_path, 'rb') as torrent_file:
                torrent_data = torrent_file.read()
            
            info_hash = str(hashlib.sha1(torrent_data).hexdigest())
            try:
                tracker_url = "http://" + tracker_url+ "/p2p" + "/upload" + "?info_hash=" + info_hash
                ip = get_local_ip()
                params = {"ip": ip,"port": self.port }  # Thêm thông tin cổng vào yêu cầu
                response = requests.get(tracker_url, params=params)
                if response.status_code == 200:
                    print("Upload to tracker successfully.")
                elif response.status_code ==201:
                    print("Already in tracker")
                else:
                    print("Failed to upload to tracker. Status code:", response.status_code)
            except Exception as e:
                print("Error connecting to tracker:", e)
        except Exception as e:
            print(f"Error uploading torrent file: {e}")

    def download_torrent_file(self, torrent_file_path, destination):
        torrent_file_name = os.path.basename(torrent_file_path)
        # Tách phần tên tệp ra khỏi phần mở rộng (ví dụ: 't.png.torrent' sẽ trở thành 't.png')
        file_name_without_extension = os.path.splitext(torrent_file_name)[0]
        file_path = os.path.join(destination, file_name_without_extension)
        destination = file_path
        try:
            with open(torrent_file_path, 'rb') as torrent_file:
                torrent_data = torrent_file.read()
            #print(torrent_data)
            decoded_torrent = bencodepy.decode(torrent_data)
            # print(f"decoded_torrent = {decoded_torrent}")
            decoded_str_keys = {convert.bytes_to_str(k): v for k, v in decoded_torrent.items()}
            # print (f"decoded_str_keys= {decoded_str_keys}")
            info_hash = str(hashlib.sha1(torrent_data).hexdigest())
            announce_url = decoded_torrent[b"announce"].decode()
            # print(f"annouce_url = {announce_url}")
            try:
                announce_url_down = "http://"+ announce_url+"/p2p"+"/download"
                #print(f"annouce_url = {announce_url_down}")
                response = requests.get(announce_url_down, params={"info_hash": info_hash})
                # Kiểm tra mã trạng thái của phản hồi
                if response.status_code == 200:
                    ip_port_pairs = response.text.split(",")
                    # Duyệt qua từng cặp ip và port
                    formatted_ip_addresses = []
                    
                    for pair in ip_port_pairs:
                        ip, port = pair.strip().split(":")
                        if port != self.port:
                            formatted_ip_addresses.append((ip, int(port)))
                    print("Current seeders in tracker:", formatted_ip_addresses)

                    threads = []
                    total_pieces = math.ceil(decoded_str_keys["info"][b"length"] / 524288)
                    print(f"Total pieces: {total_pieces}")
                    numOfThread = int(input(f"\nEnter the number of peers that you want to connect (Max {len(formatted_ip_addresses)}) : "))
                    if(numOfThread>=len(formatted_ip_addresses)): 
                        pieces_per_thread = total_pieces // len(formatted_ip_addresses) + 1
                    else:
                        pieces_per_thread = total_pieces // numOfThread + 1
                    print(f"Pieces per thread: {pieces_per_thread}")
                    start_time = time.time()
                    start_piece = 0
                    for ip_address in formatted_ip_addresses:
                        end_piece = start_piece + pieces_per_thread
                        if end_piece > total_pieces:
                            end_piece = total_pieces
                        thread = threading.Thread(target=self.download_chunk, args=(ip_address, torrent_data, destination, start_piece, end_piece, announce_url, total_pieces,torrent_file_path,start_time))
                        threads.append(thread)
                        start_piece = end_piece
                        thread.start()
                    # Wait for all threads to finish
                    for thread in threads:
                        thread.join()
                else:
                    print("Error:", response.status_code)
            except Exception as e:
                print(f"Error connecting to tracker: {e}")
        except Exception as e:
            print(f"Error downloading torrent file: {e}")

    def download_chunk(self, ip_address, file_data, destination, start_piece, end_piece, announce_url, total_pieces,file_path,start_tinme):
        for piece in range(start_piece, end_piece):
            self.download_piece(ip_address, file_data, destination, str(piece), announce_url, total_pieces,file_path,start_tinme)

    def download_piece(self, ip_address, file_data, destination, piece, announce_url, total_pieces,file_path,start_time):
        peer_ip, peer_port = ip_address
        sock = socket.create_connection((peer_ip, peer_port))
        
        sha1 = str(hashlib.sha1(file_data).hexdigest())
        payload = sha1 + " " + announce_url
        sock.sendall(payload.encode('utf-8'))
        
        response = sock.recv(1024).decode('utf-8')
        if response == "OK":
            # send interested message
            interested_payload = (2).to_bytes(4, "big") + (2).to_bytes(1, "big")
            sock.send(interested_payload)
            # received unchoke message
            unchoke_msg = sock.recv(5)
            print(f"Received unchoke message from {ip_address}: {unchoke_msg}")
            message_length, message_id = self.parse_peer_message(unchoke_msg)
            if message_id != 1:
                raise SystemError("Expecting unchoke id of 1")

            decoded_torrent = bencodepy.decode(file_data)
            decoded_str_keys = {convert.bytes_to_str(k): v for k, v in decoded_torrent.items()}
            
            # break the pieces up and send request for each
            bit_size = 512 * 1024
            final_block = b""
            piece_length = decoded_str_keys["info"][b"piece length"]
            total_length = decoded_str_keys["info"][b"length"]
            # if final piece, offset piece length
            if int(piece) == math.ceil(total_length / piece_length) -1:
                # then the piece length is the remainder
                piece_length = total_length % piece_length
            
            # Tạo tên tệp tạm thời dựa trên index của piece
            piece_filename = f"{destination}_piece_{piece}"
            
            for offset in range(0, piece_length, bit_size):
                # block length
                block_length = min(bit_size, piece_length - offset)
                print(f"Block_length {piece}:{block_length}")
                request_data = (
                    int(piece).to_bytes(4, "big")
                    + offset.to_bytes(4, "big")
                    + block_length.to_bytes(4, "big")
                )
                request_payload = (
                    (len(request_data) + 1).to_bytes(4, "big")
                    + (6).to_bytes(1, "big")
                    + request_data
                )
                sock.send(request_payload)

                message_length = int.from_bytes(sock.recv(4), "big")
                message_id = int.from_bytes(sock.recv(1), "big")
                if message_id != 7:
                    raise SystemError("Expecting piece id of 7")
                # piece_index = int.from_bytes(sock.recv(4), "big")
                # begin = int.from_bytes(sock.recv(4), "big")
                received = 0
                full_block = b""
                size_of_block = message_length - 9
                while received < size_of_block:
                    block = sock.recv(size_of_block - received)
                    full_block += block
                    received += len(block)
                final_block += full_block
                #print(f"Data cua piece{piece}:{final_block}")
                print(f"Downloading piece {piece}, offset {offset}, block length {block_length} from {ip_address}")
        
        try:
            # Lưu dữ liệu của piece vào tệp tạm thời
            with open(piece_filename, "wb") as f:
                f.write(final_block)
        except Exception as e:
            print(e)

        # Kiểm tra xem tất cả các phần đã được tải xong chưa

        downloaded_pieces = [f"{destination}_piece_{piece}" for piece in range(total_pieces)]
        d = len(list(piece_file for piece_file in downloaded_pieces if os.path.exists(piece_file)))

        print(f"Downloaded {d} pieces out of {len(downloaded_pieces)}")
        if all(os.path.exists(piece_file) for piece_file in downloaded_pieces):
            # print(f"total_length = {total_length }")
            # print(f"piece_length = {piece_length}")
            # print(f"totall piece = {total_length / piece_length}")
            piece_length = decoded_str_keys["info"][b"piece length"]
            self.merge_pieces(destination, math.ceil(total_length / piece_length))
            self.bytes += total_length  # Cập nhật số byte đã tải
            print("Download completed.")
            end_time = time.time()
            elapsed_time = end_time - start_time
            print(f"Download time: {elapsed_time} seconds")
            self.write_string_to_file(destination)
            self.upload_torrent_file(file_path,announce_url)

    def parse_peer_message(self, peer_message):
        message_length = int.from_bytes(peer_message[:4], "big")
        message_id = int.from_bytes(peer_message[4:5], "big")
        return message_length, message_id

    def handle_peer_request(self, client_socket, client_address):
        try:
            # Nhận dữ liệu từ peer
            data = client_socket.recv(1024)  # Nhận tối đa 1024 bytes
            print(f"Received data from {client_address}: {data}")

            if data is not None:
                decoded_data = data.decode('utf-8')  # Chuyển đổi byte string thành string thông thường
                parts = decoded_data.split(' ', 1)
                if len(parts) == 2:
                    data, url = parts
                    print(f"Data: {data}")
                    print(f"URL: {url}")
                
                # Tìm file tương ứng với thông tin hash nhận được
                found_files = self.find_file_by_infohash(data, url)
                print("Found files:", found_files)
                if found_files:
                    # Gửi phản hồi OK nếu peer có file
                    client_socket.sendall(b"OK")
                    # Nhận phản hồi từ peer
                    response = client_socket.recv(1024).decode()
                    unchoke_payload = self.create_unchoke_message()
                    client_socket.sendall(unchoke_payload)
                    while True:
                        # Nhận dữ liệu yêu cầu từ peer
                        request_length = int.from_bytes(client_socket.recv(4), "big")
                        request_id = int.from_bytes(client_socket.recv(1), "big")
                        print(f"Received request ID: {request_id}")
                        if request_id != 6:
                            print("Download completed. Closing connection.")
                            return
                        
                        
                        # Nhận dữ liệu yêu cầu
                        request_data = client_socket.recv(request_length - 1)  # Trừ đi 1 byte đã nhận cho request_id
                        
                        # Phân tích dữ liệu yêu cầu
                        piece_index = int.from_bytes(request_data[:4], "big")
                        offset = int.from_bytes(request_data[4:8], "big")
                        block_length = int.from_bytes(request_data[8:], "big")
                        
                        # Xử lý yêu cầu và lấy dữ liệu cần gửi lại cho peer
                        response_data = self.get_response_data(piece_index, offset, block_length, found_files[0])
                        
                        # Gửi dữ liệu phản hồi cho peer
                        response_length = len(response_data) + 9  # 9 bytes cho piece_index, offset và response_id
                        response_payload = (
                            response_length.to_bytes(4, "big")  # Chiều dài của tin nhắn phản hồi
                            + (7).to_bytes(1, "big")  # ID của tin nhắn phản hồi (7 cho "piece")
                            + piece_index.to_bytes(4, "big")  # Chỉ số của mảnh
                            + offset.to_bytes(4, "big")  # Độ lệch bắt đầu của khối trong mảnh
                            + response_data  # Dữ liệu khối được yêu cầu
                        )
                        client_socket.sendall(response_payload) # Gửi dữ liệu phản hồi cho peer
                else:
                    # Gửi phản hồi NOT FOUND nếu peer không có file
                    client_socket.sendall(b"NOT FOUND")
            else:
                print("Không thể trích xuất info hash từ dữ liệu handshake.")
        except Exception as e:
            print("Error handling peer request :", e)

    def read_peer_file_path(self):
        file_name = f"info_{self.port}.txt"
        file_dir = "peer_file_path"
        file_path = os.path.join(file_dir, file_name)   
        strings = []

        # Đọc các chuỗi từ file
        try:
            with open(file_path, 'r') as file:
                for line in file:
                    strings.append(line.strip())
        except FileNotFoundError:
            pass  # Bỏ qua lỗi nếu file không tồn tại

        return strings

    def find_file_by_infohash(self, infohash, url):
        found_files = []
        file_paths = self.read_peer_file_path()
        #print(f"File paht = {file_paths}")
        # Duyệt qua tất cả các tệp tin và thư mục trong đường dẫn start_path
        for file_path in file_paths:
            try:
                # Kiểm tra quyền truy cập của tệp tin hoặc thư mục
                os.access(file_path, os.R_OK)
                # Tính thông tin hash của tệp tin
                calculated_infohash = convert.get_metadata_hash(file_path, url)
                print(f"Calculated info hash: {calculated_infohash}")
                print(f"Received info hash: {infohash}")
                # So sánh thông tin hash của tệp tin với thông tin hash được cung cấp
                if calculated_infohash == infohash:
                    found_files.append(file_path)                     
            except PermissionError:
                # Bỏ qua các tệp tin hoặc thư mục mà không có quyền truy cập
                pass
            except FileNotFoundError:
                # Bỏ qua các lỗi "No such file or directory"
                pass

        return found_files

    def create_unchoke_message(self):
        # Định dạng của tin nhắn "unchoke": <length prefix><message ID>
        # - Độ dài của tin nhắn là 1 byte (vì không có dữ liệu cụ thể được gửi kèm theo)
        # - Message ID của tin nhắn unchoke là 1
        message_length = (1).to_bytes(4, "big")
        message_id = (1).to_bytes(1, "big")
        unchoke_payload = message_length + message_id
        return unchoke_payload

    def get_response_data(self, piece_index, offset, block_length, file_path, piece_length=512*1024):
        # Open the file for reading in binary mode
        with open(file_path, "rb") as file:
            # Calculate the start position in the file for the requested piece and offset
            piece_start_position = piece_index * piece_length + offset
            # Move to the start position in the file
            file.seek(piece_start_position)
            # Read the block of data from the file
            print(f"Reading piece {piece_index}, offset {offset}, block length {block_length}")
            data = file.read(block_length)
        return data

    def merge_pieces(self, destination, total_pieces):
        try:
            with open(destination, "wb") as f_dest:
                for piece_index in range(total_pieces):
                    piece_filename = f"{destination}_piece_{piece_index}"
                    if os.path.exists(piece_filename):
                        with open(piece_filename, "rb") as f_piece:
                            f_dest.write(f_piece.read())
                        os.remove(piece_filename)  # Xóa tệp tạm thời sau khi ghép vào tệp hoàn chỉnh
                    else:
                        print(f"Temporary file {piece_filename} not found")
            print(f"Merged temporary files into {destination}")
        except Exception as e:
            print(f"Error merging temporary files: {e}")
    def disconnect_to_tracker(self, file_path, tracker_url):
        try:
            # Đọc dữ liệu từ file torrent
            with open(file_path, 'rb') as torrent_file:
                torrent_data = torrent_file.read()
            
            info_hash = str(hashlib.sha1(torrent_data).hexdigest())
            try:
                tracker_url = "http://" + tracker_url+ "/p2p" + "/disconnect" + "?info_hash=" + info_hash
                ip = get_local_ip()
                params = {"ip": ip,"port": self.port }  # Thêm thông tin cổng vào yêu cầu
                response = requests.get(tracker_url, params=params)
                if response.status_code == 200:
                    print("Disconnect to tracker successfully")
                elif response.status_code == 201:
                    print("Peer is not existing in tracker")
                else:
                    print("Failed to disconnect to tracker. Status code:", response.status_code)
            except Exception as e:
                print("Error disconnecting to tracker:", e)
        except Exception as e:
            print(f"Error uploading torrent file: {e}")


# def get_local_ip(interface='enp0s3'):
#     # Chạy lệnh ifconfig và lấy kết quả
#     result = subprocess.run(['ifconfig', interface], capture_output=True, text=True)

#     # Phân tích kết quả để tìm địa chỉ IP
#     ip_pattern = r'inet (\d+\.\d+\.\d+\.\d+)'
#     match = re.search(ip_pattern, result.stdout)

#     # Trả về địa chỉ IP nếu tìm thấy, nếu không trả về None
#     if match:
#         return match.group(1)
#     else:
#         return None
    
def get_local_ip():
    # Sử dụng socket để lấy IP cục bộ
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return local_ip
    except Exception as e:
        print(f"Error getting local IP: {e}")
        return None

# if __name__ == "__main__":
#     peer = Peer()
#     try:
#         peer.port = peer.find_empty_port()
#         print(f"Peer is listening on {get_local_ip()}:{peer.port}")
#         # Create a new socket for listening to peer connections
#         peer.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        
#         peer.listen_socket.bind((get_local_ip(), peer.port)) 
#         # print ip address of local that other can see 
        
#         peer.listen_socket.listen(5)

#         # Define a function to handle user input
#         def handle_user_input():
#             while True:
#                 command = input("\nEnter command: ")
#                 command_parts = command.split()

#                 # if command.lower() == "stop":
#                 #     print("Number of bytes download: ", peer.bytes)
#                 #     # Đóng socket nghe khi kết thúc chương trình
#                 #     peer.listen_socket.close()
#                 #     break
#                 if command.startswith("create"):
#                     if len(command_parts) >= 4:
#                         file_path = command_parts[1]
#                         file_dir = command_parts[2]
#                         url = command_parts[3]
#                         file_name = os.path.basename(file_path)
#                         peer.create_torrent_file(file_path, file_dir, url)
#                         print(f"Torrent file is created for {file_name}")
#                     else:
#                         print(f"Torrent file can not be created for {file_name}")
#                 elif command.startswith("upload"):
#                     if len(command_parts) >= 3:
#                         torrent_file_path = command_parts[1]
#                         new_url = command_parts[2]
#                         if os.path.isfile(torrent_file_path):
#                             peer.upload_torrent_file(torrent_file_path, new_url)
#                         else:
#                             print("Error: Torrent file not found.")
#                     else:
#                         print("Invalid command: Missing file name.")
#                 elif command.startswith("download"):
#                     if len(command_parts) >= 3:
#                         torrent_file_path = command_parts[1]
#                         destination = command_parts[2]
#                         # Gửi yêu cầu tải file từ tracker
#                         if os.path.isfile(torrent_file_path):
#                             peer.download_torrent_file(torrent_file_path, destination)
#                         else:
#                             print("Error: Torrent file not found.")
#                 elif command.startswith("disconnect"):
#                     if len(command_parts) >= 3:
#                         torrent_file_path = command_parts[1]
#                         disconnect_url = command_parts[2]
#                         if os.path.isfile(torrent_file_path):
#                             peer.disconnect_to_tracker(torrent_file_path, disconnect_url)
#                         else:
#                             print("Error: Torrent file not found.")
#                     else:
#                         print("Invalid command: Missing file name.")
           
#         # Create a thread for handling user input
#         user_input_thread = threading.Thread(target=handle_user_input)
#         user_input_thread.start()

#         while True:
#             client_socket, client_address = peer.listen_socket.accept()
#             print(f"Accepted connection from {client_address}")
#             threading.Thread(target=peer.handle_peer_request, args=(client_socket, client_address)).start()
#     except Exception as e:
#         print(f"Error occurred: {e}")

def start_peer(peer):
    try:
        peer.port = peer.find_empty_port()
        print(f"Peer is listening on {get_local_ip()}:{peer.port}")
        peer.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        peer.listen_socket.bind((get_local_ip(), peer.port))
        peer.listen_socket.listen(5)

        def accept_connections():
            while True:
                client_socket, client_address = peer.listen_socket.accept()
                print(f"Accepted connection from {client_address}")
                threading.Thread(target=peer.handle_peer_request, args=(client_socket, client_address)).start()

        threading.Thread(target=accept_connections, daemon=True).start()
    except Exception as e:
        print(f"Error occurred: {e}")

# Tạo GUI bằng tkinter
class App:
    def __init__(self, root, peer):
        self.root = root
        self.peer = peer
        root.title("Torrent Client GUI")

        # Nút CREATE
        self.create_frame = tk.LabelFrame(root, text="Create Torrent")
        self.create_frame.pack(fill="x", padx=10, pady=5)

        self.file_path_label = tk.Label(self.create_frame, text="File path:")
        self.file_path_label.pack(side="left")
        self.file_path_entry = tk.Entry(self.create_frame, width=40)
        self.file_path_entry.pack(side="left", padx=5)
        self.browse_button = tk.Button(self.create_frame, text="Browse", command=self.browse_file)
        self.browse_button.pack(side="left")
        
        self.tracker_url_label = tk.Label(self.create_frame, text="Tracker URL:")
        self.tracker_url_label.pack(side="left", padx=5)
        self.tracker_url_entry = tk.Entry(self.create_frame, width=30)
        self.tracker_url_entry.pack(side="left", padx=5)
        
        self.file_dir_label = tk.Label(self.create_frame, text="Output dir:")
        self.file_dir_label.pack(side="left", padx=5)
        self.file_dir_entry = tk.Entry(self.create_frame, width=20)
        self.file_dir_entry.pack(side="left", padx=5)

        self.create_button = tk.Button(self.create_frame, text="Create", command=self.create_torrent)
        self.create_button.pack(side="left", padx=5)

        # Nút UPLOAD
        self.upload_frame = tk.LabelFrame(root, text="Upload Torrent")
        self.upload_frame.pack(fill="x", padx=10, pady=5)

        self.upload_torrent_label = tk.Label(self.upload_frame, text="Torrent file:")
        self.upload_torrent_label.pack(side="left")
        self.upload_torrent_entry = tk.Entry(self.upload_frame, width=40)
        self.upload_torrent_entry.pack(side="left", padx=5)
        self.upload_browse_button = tk.Button(self.upload_frame, text="Browse", command=self.browse_torrent)
        self.upload_browse_button.pack(side="left")

        self.upload_tracker_url_label = tk.Label(self.upload_frame, text="Tracker URL:")
        self.upload_tracker_url_label.pack(side="left", padx=5)
        self.upload_tracker_url_entry = tk.Entry(self.upload_frame, width=30)
        self.upload_tracker_url_entry.pack(side="left", padx=5)

        self.upload_button = tk.Button(self.upload_frame, text="Upload", command=self.upload_torrent)
        self.upload_button.pack(side="left", padx=5)

        # Nút DOWNLOAD
        self.download_frame = tk.LabelFrame(root, text="Download Torrent")
        self.download_frame.pack(fill="x", padx=10, pady=5)

        self.download_torrent_label = tk.Label(self.download_frame, text="Torrent file:")
        self.download_torrent_label.pack(side="left")
        self.download_torrent_entry = tk.Entry(self.download_frame, width=40)
        self.download_torrent_entry.pack(side="left", padx=5)
        self.download_torrent_browse_button = tk.Button(self.download_frame, text="Browse", command=self.browse_torrent_download)
        self.download_torrent_browse_button.pack(side="left")

        self.destination_label = tk.Label(self.download_frame, text="Destination:")
        self.destination_label.pack(side="left", padx=5)
        self.destination_entry = tk.Entry(self.download_frame, width=30)
        self.destination_entry.pack(side="left", padx=5)

        self.download_button = tk.Button(self.download_frame, text="Download", command=self.download_torrent)
        self.download_button.pack(side="left", padx=5)

        # Nút DISCONNECT
        self.disconnect_frame = tk.LabelFrame(root, text="Disconnect Torrent")
        self.disconnect_frame.pack(fill="x", padx=10, pady=5)

        self.disconnect_torrent_label = tk.Label(self.disconnect_frame, text="Torrent file:")
        self.disconnect_torrent_label.pack(side="left")
        self.disconnect_torrent_entry = tk.Entry(self.disconnect_frame, width=40)
        self.disconnect_torrent_entry.pack(side="left", padx=5)
        self.disconnect_torrent_browse_button = tk.Button(self.disconnect_frame, text="Browse", command=self.browse_torrent_disconnect)
        self.disconnect_torrent_browse_button.pack(side="left")

        self.disconnect_tracker_label = tk.Label(self.disconnect_frame, text="Tracker URL:")
        self.disconnect_tracker_label.pack(side="left", padx=5)
        self.disconnect_tracker_entry = tk.Entry(self.disconnect_frame, width=30)
        self.disconnect_tracker_entry.pack(side="left", padx=5)

        self.disconnect_button = tk.Button(self.disconnect_frame, text="Disconnect", command=self.disconnect_torrent)
        self.disconnect_button.pack(side="left", padx=5)

    def browse_file(self):
        path = filedialog.askopenfilename()
        if path:
            self.file_path_entry.delete(0, tk.END)
            self.file_path_entry.insert(0, path)

    def browse_torrent(self):
        path = filedialog.askopenfilename(filetypes=[("Torrent files", "*.torrent")])
        if path:
            self.upload_torrent_entry.delete(0, tk.END)
            self.upload_torrent_entry.insert(0, path)

    def browse_torrent_download(self):
        path = filedialog.askopenfilename(filetypes=[("Torrent files", "*.torrent")])
        if path:
            self.download_torrent_entry.delete(0, tk.END)
            self.download_torrent_entry.insert(0, path)

    def browse_torrent_disconnect(self):
        path = filedialog.askopenfilename(filetypes=[("Torrent files", "*.torrent")])
        if path:
            self.disconnect_torrent_entry.delete(0, tk.END)
            self.disconnect_torrent_entry.insert(0, path)

    def create_torrent(self):
        f = self.file_path_entry.get()
        d = self.file_dir_entry.get()
        url = self.tracker_url_entry.get()
        if os.path.isfile(f) and url and d:
            info_hash = self.peer.create_torrent_file(f, d, url)
            messagebox.showinfo("Create Torrent", f"Torrent created with info hash: {info_hash}")
        else:
            messagebox.showwarning("Create Torrent", "Invalid input!")

    def upload_torrent(self):
        torrent_file = self.upload_torrent_entry.get()
        url = self.upload_tracker_url_entry.get()
        if os.path.isfile(torrent_file) and url:
            self.peer.upload_torrent_file(torrent_file, url)
            messagebox.showinfo("Upload Torrent", "Upload request sent")
        else:
            messagebox.showwarning("Upload Torrent", "Invalid input!")

    def download_torrent(self):
        torrent_file = self.download_torrent_entry.get()
        dest = self.destination_entry.get()
        if os.path.isfile(torrent_file) and dest:
            threading.Thread(target=self.peer.download_torrent_file, args=(torrent_file, dest), daemon=True).start()
            messagebox.showinfo("Download Torrent", "Download started in background")
        else:
            messagebox.showwarning("Download Torrent", "Invalid input!")

    def disconnect_torrent(self):
        torrent_file = self.disconnect_torrent_entry.get()
        url = self.disconnect_tracker_entry.get()
        if os.path.isfile(torrent_file) and url:
            self.peer.disconnect_to_tracker(torrent_file, url)
            messagebox.showinfo("Disconnect Torrent", "Disconnect request sent")
        else:
            messagebox.showwarning("Disconnect Torrent", "Invalid input!")

if __name__ == "__main__":
    peer = Peer()
    start_peer(peer)

    root = tk.Tk()
    app = App(root, peer)
    root.mainloop()