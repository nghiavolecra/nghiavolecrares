import socket
import os
import bencodepy
import threading
import sys
import transform
import requests
import hashlib
import math
import subprocess
from urllib.request import urlopen
import re
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import base64

local_ip = ""

class StartPage(tk.Frame):
    def __init__(self,parent, appController,peer):
        tk.Frame.__init__(self,parent)

        label_title = tk.Label(self, text='LOG IN', font=('Arial', 25))
        label_user = tk.Label(self, text='Username')
        label_pswd = tk.Label(self, text='Password')

        self.label_notice = tk.Label(self,text='',fg='red')
        self.entry_user = tk.Entry(self, width=30,bg='light yellow')
        self.entry_pswd = tk.Entry(self, width=30,bg='light yellow',show='●')
        self.tracker_button = tk.Label(self, text='Tracker URL')
        self.entry_tracker = tk.Entry(self, width=30,bg='light yellow')
        button_log = tk.Button(self, text='LOG IN', command=lambda: appController.logIn(self,peer))
        button_log.configure(width=10)

        label_title.pack()
        label_user.pack()
        self.entry_user.pack()
        label_pswd.pack()
        self.entry_pswd.pack()
        self.tracker_button.pack()
        self.entry_tracker.pack()
        self.label_notice.pack()
        button_log.pack()     
    def clear_entries(self):
        self.entry_user.delete(0, tk.END)
        self.entry_pswd.delete(0, tk.END)
        self.label_notice.config(text='') 
class CreateTorrent(tk.Frame):
    def __init__(self,parent, appController,peer):
        tk.Frame.__init__(self, parent)
        label_title = tk.Label(self, text="Create Torrent File", font=("Arial", 16))
        label_title.pack(pady=10)
        self.filepath = ""
        self.filedir = ""

        self.choose_button = tk.Button(self, text="Choose file ...",command=self.choose_file ,width=15)
        self.choose_button.pack(pady=10)

        self.file_choose = tk.Label(self, text="",font=("Arial",12))
        # self.entry_tracker = tk.Entry(self, width=30,bg='light yellow')
        self.file_choose.pack(pady=10)
        # self.entry_tracker.pack()

        self.create_button = tk.Button(self, text="Create Torrent",command=lambda: self.create_torrent(appController,peer) ,width=15)
        self.create_button.pack(pady=10)

        self.back_button = tk.Button(self, text="Back",command=lambda: appController.showPage(HomePage) ,width=15)
        self.back_button.pack(pady=10)

    
    def choose_file(self):
        file_path = filedialog.askopenfilename(title="Select a File")
        self.filepath = file_path
        self.file_choose.config(text=self.filepath)
        self.filedir = os.path.dirname(file_path)
    def create_torrent(self,appController,peer):
        tracker = peer.tracker_url
        if self.filepath == "" or self.filedir == "" or tracker == "":
             messagebox.showinfo("Note", "Fields cannot be empty")
             return
        else:
            filepath = self.filepath
            filedir = self.filedir
            peer.create_torrent_file(filepath, filedir, tracker)
            messagebox.showinfo("Note", "Create torrent file successfully!")
            self.file_choose.config(text="")
            appController.showPage(HomePage)
class HomePage(tk.Frame):
    def __init__(self,parent, appController,peer):
        tk.Frame.__init__(self, parent)
        label_title = tk.Label(self, text="File Sharing Application", font=("Arial", 16))
        label_title.pack(pady=10)
        self.uploaded_files = []

        self.torrent_button = tk.Button(self, text="Create Torrent",command=lambda: appController.showPage(CreateTorrent), width=15)
        self.torrent_button.pack(pady=5)

        # Nút bấm Upload
        self.upload_button = tk.Button(self, text="Upload File", command=lambda: self.upload_file(peer), width=15)
        self.upload_button.pack(pady=5)

       
        # Nút bấm Download
        self.download_button = tk.Button(self, text="Download File", command=lambda: self.download_file(peer), width=15)
        self.download_button.pack(pady=5)

        self.refresh_button = tk.Button(self, text="Refresh",command=lambda:self.refresh(peer) ,width=15)
        self.refresh_button.pack(pady=5)

        self.btn_log_out = tk.Button(self, text="Log Out", command=lambda: appController.showPage(StartPage), width=15)
        self.download_button.pack(pady=5)

        # Giao diện hiển thị danh sách file
        self.file_list_frame = ttk.Frame(self)
        self.file_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Treeview với hai cột: STT và Tên file
        self.file_list_tree = ttk.Treeview(
            self.file_list_frame, columns=("addr", "file_name"), show="headings"
        )
        self.file_list_tree.heading("addr", text="Address")
        self.file_list_tree.heading("file_name", text="Torrent Files")
        self.file_list_tree.column("addr", width=50, anchor="center")  # Căn giữa cột STT
        self.file_list_tree.column("file_name", width=500, anchor="w")  # Căn trái tên file
        self.file_list_tree.pack(fill=tk.BOTH, expand=True)

        # Thanh cuộn dọc cho danh sách file
        scrollbar = ttk.Scrollbar(self.file_list_frame, orient=tk.VERTICAL, command=self.file_list_tree.yview)
        self.file_list_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    def refresh(self,peer):
        self.uploaded_files = peer.refresh_server()
        for item in self.file_list_tree.get_children():
            self.file_list_tree.delete(item)
        for item in self.uploaded_files:
            self.file_list_tree.insert("", tk.END, values=(item["address"], item["file_name"]))
    def upload_file(self,peer):
        """Hàm xử lý khi nhấn nút Upload."""
        file_path = filedialog.askopenfilename(
            title="Select a File",
            filetypes=(("Torrent files", "*.torrent"), ("All files", "*.*"))  # Bộ lọc thêm file .torrent
        )
        if file_path.find(".torrent") == -1:
            messagebox.showerror("Error", "File must be torrent!")
            return
        if file_path:
            try:
                response1 = peer.upload_torrent_file(file_path)
                # Đọc nội dung file (xử lý file nhị phân nếu cần)
                with open(file_path, "rb") as file:  # Mở file ở chế độ nhị phân
                    content = file.read()
                encoded_content = base64.b64encode(content).decode("utf-8")
                # Lưu tên file và nội dung vào danh sách
                file_name = file_path.split("/")[-1]
                sendData = {"file_name": file_name, "content": encoded_content, "address": f"{local_ip}:{peer.port}"}
                response2 = peer.send_torrent(sendData)
                # Thêm file vào Treeview với STT
                self.refresh(peer)

                # Hiển thị thông báo
                messagebox.showinfo("Note", f"{response1}\n{response2}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to read file: {e}")
    def download_file(self,peer):
        """Hàm xử lý khi nhấn nút Download."""
        selected_item = self.file_list_tree.selection()  # Lấy ID của dòng được chọn
        if not selected_item:
            messagebox.showwarning("No Selection", "Please select a file to download!")
            return
        save_path = None
        for item_id in selected_item:
            # Lấy số thứ tự từ Treeview
            item = self.file_list_tree.item(item_id)
            #stt = item["values"][0] - 1  # STT trong Treeview bắt đầu từ 1, index trong danh sách bắt đầu từ 0
            file_data = next((data for data in self.uploaded_files if data["address"] == item["values"][0] and data["file_name"] == item["values"][1]), {})
            # Lấy thông tin file từ danh sách
            file_name = file_data["file_name"]
            torrent_data = file_data["content"]
            torrent_data = base64.b64decode(torrent_data.encode("utf-8"))
        # Hộp thoại chọn vị trí lưu file
            if not save_path:
                save_path = filedialog.asksaveasfilename(
                    title="Save File As",
                    initialfile=".".join(file_name.split(".")[:-1]),
                    defaultextension="",  # Không đặt phần mở rộng mặc định
                    filetypes=(("All files", "*.*"), ("Torrent files", "*.torrent"))
                )
            else: save_path = os.path.dirname(save_path) + "/" + ".".join(file_name.split(".")[:-1])
            if save_path:
                try:
                # Ghi nội dung file vào vị trí được chọn (nhị phân)
                    peer.download_torrent_file(torrent_data, save_path)
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save file: {e}")
        messagebox.showinfo("Download Successful", f"File saved as '{save_path}'!")   

class App(tk.Tk):
    def __init__(self,peer):
        tk.Tk.__init__(self)
        self.account = [('binh2308','1'),('phong2808','1')]
        self.title(f'Peer {peer.port}')
        self.geometry("800x500")
        self.resizable(width=False, height=False)

        container = tk.Frame()

        container.pack(side='top',fill='both',expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        self.frames = {}
        for F in (StartPage, HomePage, CreateTorrent):
            frame = F(container, self,peer)
            frame.grid(row=0, column=0,sticky='nsew')
            self.frames[F] = frame
        self.frames[StartPage].tkraise()
    def showPage(self, FrameClass):
        if FrameClass == StartPage:
            self.frames[FrameClass].clear_entries()
        self.frames[FrameClass].tkraise()    
    def compareAccount(self,user,password):
        for acc in self.account:
            if user == acc[0] and password == acc[1]:
                return True
        return False
    def logIn(self, curFrame,peer):
        try:
            user = curFrame.entry_user.get()
            pswd = curFrame.entry_pswd.get()
            tracker_url = curFrame.entry_tracker.get()
            if user == "" or pswd == "" or tracker_url == "":
                curFrame.label_notice["text"] = "Fields cannot be empty"
                return
            peer.tracker_url = tracker_url
            compare = self.compareAccount(user,pswd)
            if(compare):
                self.showPage(HomePage)
            else: 
                curFrame.label_notice["text"] = "Invalid username or password"
                return
        except Exception as e:
            print("Error: ", e)
       

class Peer:
    def __init__(self):
        self.listen_socket = None 
        self.port = None
        self.bytes = 0
        self.file_path = []
        self.tracker_url = ""
    def find_empty_port(self, start_port=8000, end_port=8100):
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
    def send_torrent(self,data):
        tracker_url = self.tracker_url + "/send-torrent"
        response = requests.post(tracker_url, json=data)
        if response.status_code == 200:
              data = response.text
              return data
        else: return "Fail to send file to server"
    def write_string_to_file(self, string):
        file_name = f"info_{self.port}.txt"
        file_dir = "peer_directory"
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
        with open(file_path, 'w') as file:
            for unique_string in unique_strings:
                file.write(unique_string + '\n')

    def create_torrent_file(self, file_path, file_dir, tracker_url):
        self.tracker_url = tracker_url
        file_name = os.path.basename(file_path)
        self.write_string_to_file(file_path)
        print(f"Creating torrent file for {file_name}...")
        info_hash = transform.create_torrent(file_path, tracker_url, os.path.join(file_dir, f'{file_name}.torrent'))
    def refresh_server(self):
        try:
            tracker_url = self.tracker_url + "/get-list"
            response = requests.get(tracker_url)
            if response.status_code == 200:
                data = response.json()
                return data
            else: return []
        except Exception as e:
            return []
    def upload_torrent_file(self, file_path):
        try:
            # Đọc dữ liệu từ file torrent
            with open(file_path, 'rb') as torrent_file:
                torrent_data = torrent_file.read()
            
            info_hash = str(hashlib.sha1(torrent_data).hexdigest())
            try:
                tracker_url = self.tracker_url + "/announce/upload" + "?info_hash=" + info_hash
                params = {"ip": get_local_ip(),"port": self.port}  # Thêm thông tin cổng vào yêu cầu
                response = requests.get(tracker_url, params=params)
                if response.status_code == 200:
                    return  "Upload to tracker successfully."
                else:
                    return f"Failed to upload to tracker. Status code: {response.status_code}" 
            except Exception as e:
                return f"Error connecting to tracker: {e}"
        except Exception as e:
           return f"Error uploading torrent file: {e}"

    def download_torrent_file(self, torrent_data, destination):
       
        try:
            decoded_torrent = bencodepy.decode(torrent_data)
            decoded_str_keys = {transform.bytes_to_str(k): v for k, v in decoded_torrent.items()}

            info_hash = str(hashlib.sha1(torrent_data).hexdigest())
            announce_url = decoded_torrent[b"announce"].decode()
                
            try:
                announce_url_down = announce_url + "/announce/download"
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
                    print("Formatted IP addresses:", formatted_ip_addresses)

                    threads = []
                    total_pieces = math.ceil(decoded_str_keys["info"][b"length"] / decoded_str_keys["info"][b"piece length"])
                    print(f"Total pieces: {total_pieces}")
                    pieces_per_thread = total_pieces // len(formatted_ip_addresses) + 1
                    print(f"Pieces per thread: {pieces_per_thread}")
                    start_piece = 0
                    for ip_address in formatted_ip_addresses:
                        end_piece = start_piece + pieces_per_thread
                        if end_piece > total_pieces:
                            end_piece = total_pieces
                        thread = threading.Thread(target=self.download_range, args=(ip_address, torrent_data, destination, start_piece, end_piece, announce_url, total_pieces))
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

    def download_range(self, ip_address, file_data, destination, start_piece, end_piece, announce_url, total_pieces):
        for piece in range(start_piece, end_piece):
            self.download_piece(ip_address, file_data, destination, str(piece), announce_url, total_pieces)

    def download_piece(self, ip_address, file_data, destination, piece, announce_url, total_pieces):
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
            decoded_str_keys = {transform.bytes_to_str(k): v for k, v in decoded_torrent.items()}
            
            # break the pieces up and send request for each
            bit_size = 16 * 1024
            final_block = b""
            piece_length = decoded_str_keys["info"][b"piece length"]
            total_length = decoded_str_keys["info"][b"length"]
            # if final piece, offset piece length
            if int(piece) == math.ceil(total_length / piece_length) - 1:
                # then the piece length is the remainder
                piece_length = total_length % piece_length
            
            # Tạo tên tệp tạm thời dựa trên index của piece
            piece_filename = f"{destination}_piece_{piece}"
            
            for offset in range(0, piece_length, bit_size):
                # block length
                block_length = min(bit_size, piece_length - offset)
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
                piece_index = int.from_bytes(sock.recv(4), "big")
                begin = int.from_bytes(sock.recv(4), "big")
                received = 0
                full_block = b""
                size_of_block = message_length - 9
                while received < size_of_block:
                    block = sock.recv(size_of_block - received)
                    full_block += block
                    received += len(block)
                final_block += full_block
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
            self.merge_temp_files(destination, math.ceil(total_length / piece_length))
            self.bytes += total_length  # Cập nhật số byte đã tải
            print("Download completed.")

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
                            break
                        
                        
                        # Nhận dữ liệu yêu cầu
                        request_data = client_socket.recv(request_length - 1)  # Trừ đi 1 byte đã nhận cho request_id
                        
                        # Phân tích dữ liệu yêu cầu
                        piece_index = int.from_bytes(request_data[:4], "big")
                        offset = int.from_bytes(request_data[4:8], "big")
                        block_length = int.from_bytes(request_data[8:], "big")
                        
                        # Xử lý yêu cầu và lấy dữ liệu cần gửi lại cho peer
                        response_data = self.process_request(piece_index, offset, block_length, found_files[0])
                        
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
            print("Error handling peer request:", e)

    def read_strings_from_file(self):
        file_name = f"info_{self.port}.txt"
        file_dir = "peer_directory"
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
        file_paths = self.read_strings_from_file()
        # Duyệt qua tất cả các tệp tin và thư mục trong đường dẫn start_path
        for file_path in file_paths:
            try:
                # Kiểm tra quyền truy cập của tệp tin hoặc thư mục
                os.access(file_path, os.R_OK)
                # Tính thông tin hash của tệp tin
                calculated_infohash = transform.get_info_hash(file_path, url)
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

    def process_request(self, piece_index, offset, block_length, file_path, piece_length=2**20):
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

    def merge_temp_files(self, destination, total_pieces):
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

    def merge_temp_files(self, destination, total_pieces):
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
    def start_server(self):
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        self.listen_socket.bind((get_local_ip(), peer.port)) 
        # print ip address of local that other can see 
        self.listen_socket.listen(5)
        while True:
            client_socket, client_address = self.listen_socket.accept()
            print(f"Accepted connection from {client_address}")
            threading.Thread(target=self.handle_peer_request, args=(client_socket, client_address)).start()
            #self.handle_peer_request(client_socket, client_address)
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

if __name__ == "__main__":
    peer = Peer()
    try:
        local_ip = get_local_ip()
        peer.port = peer.find_empty_port()
        print(f"Peer is listening on {local_ip}:{peer.port}")
        # Create a new socket for listening to peer connections
        server_thread = threading.Thread(target=peer.start_server,daemon=True)
        server_thread.start()
        app = App(peer)
        app.mainloop()
        # Define a function to handle user input
        # def handle_user_input():
        #     while True:
        #         command = input("\nEnter command: ")
        #         command_parts = command.split()

        #         if command.lower() == "stop":
        #             print("Number of bytes download: ", peer.bytes)
        #             # Đóng socket nghe khi kết thúc chương trình
        #             peer.listen_socket.close()
        #             break
        #         elif command.startswith("create"):
        #             if len(command_parts) >= 4:
        #                 file_path = command_parts[1]
        #                 file_dir = command_parts[2]
        #                 url = command_parts[3]
        #                 file_name = os.path.basename(file_path)
        #                 peer.create_torrent_file(file_path, file_dir, url)
        #                 print(f"Torrent file is created for {file_name}")
        #             else:
        #                 print(f"Torrent file can not be created for {file_name}")
        #         elif command.startswith("upload"):
        #             if len(command_parts) >= 3:
        #                 torrent_file_path = command_parts[1]
        #                 new_url = command_parts[2]
        #                 if os.path.isfile(torrent_file_path):
        #                     peer.upload_torrent_file(torrent_file_path, new_url)
        #                 else:
        #                     print("Error: Torrent file not found.")
        #             else:
        #                 print("Invalid command: Missing file name.")
        #         elif command.startswith("download"):
        #             if len(command_parts) >= 3:
        #                 torrent_file_path = command_parts[1]
        #                 destination = command_parts[2]
        #                 # Gửi yêu cầu tải file từ tracker
        #                 if os.path.isfile(torrent_file_path):
        #                     peer.download_torrent_file(torrent_file_path, destination)
        #                 else:
        #                     print("Error: Torrent file not found.")
           
        # # Create a thread for handling user input
        # user_input_thread = threading.Thread(target=handle_user_input)
        # user_input_thread.start()
    except Exception as e:
        print(f"Error occurred: {e}")    #""C:/Users/PC/Desktop/test/test.docx""