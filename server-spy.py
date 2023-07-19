from PyQt5.QtCore import pyqtSignal, pyqtSlot, QThread, Qt
from PyQt5.QtWidgets import QAbstractItemView, QLabel, QListWidget, QLineEdit, QDialog, QPushButton, QHBoxLayout, \
    QVBoxLayout, QApplication, QProgressBar, QListWidgetItem
import paramiko
import webbrowser

global_server_list = {}

target_server = None

class MyMainGUI(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.add_button = QPushButton("서버 추가")
        self.github_button = QPushButton("최신 버전 다운로드 (GitHub)")
        self.add_IP = QLineEdit(self)
        self.IP_label = QLabel("IP :", self)
        self.add_ID = QLineEdit(self)
        self.ID_label = QLabel("ID :", self)
        self.add_PW = QLineEdit(self)
        self.add_PW.setEchoMode(QLineEdit.Password)
        self.PW_label = QLabel("PW :", self)
        self.add_PORT = QLineEdit(self)
        self.PORT_label = QLabel("PORT :", self)
        self.add_PORT.setText("22")
        self.server_list = QListWidget(self)
        self.server_list.resize(600, 600)
        
        self.cpu_bar = QProgressBar(self)
        self.mem_bar = QProgressBar(self)
        self.gpu_bar = []
        for i in range(8):
            self.gpu_bar.append(QProgressBar(self))

        self.cpu_bar.setRange(0, 100)
        self.mem_bar.setRange(0, 100)
        for i in range(8):
            self.gpu_bar[i].setRange(0, 100)

        self.status_label = QLabel("", self)

        self.cpu_label = QLabel("CPU : ", self)
        self.mem_label = QLabel("MEM : ", self)
        self.gpu_label = []
        for i in range(8):
            self.gpu_label.append(QLabel("GPU{} : ".format(i), self))

        self.search_button = QPushButton("서버 (재)검색")

        hbox = QHBoxLayout()
        hbox.addStretch(0)
        hbox.addWidget(self.IP_label)
        hbox.addWidget(self.add_IP)
        hbox.addWidget(self.ID_label)
        hbox.addWidget(self.add_ID)
        hbox.addWidget(self.PW_label)
        hbox.addWidget(self.add_PW)
        hbox.addWidget(self.PORT_label)
        hbox.addWidget(self.add_PORT)
        hbox.addWidget(self.add_button)
        hbox.addStretch(0)

        github_hbox = QHBoxLayout()
        github_hbox.addWidget(self.github_button)

        label_vbox = QVBoxLayout()
        label_vbox.addWidget(self.cpu_label)
        label_vbox.addWidget(self.mem_label)
        for i in range(8):
            label_vbox.addWidget(self.gpu_label[i])

        status_vbox = QVBoxLayout()
        status_vbox.addWidget(self.cpu_bar)
        status_vbox.addWidget(self.mem_bar)
        for i in range(8):
            status_vbox.addWidget(self.gpu_bar[i])

        hbox2 = QHBoxLayout()
        hbox2.addWidget(self.server_list)
        hbox2.addLayout(label_vbox)
        hbox2.addLayout(status_vbox)

        hbox3 = QHBoxLayout()
        hbox3.addWidget(self.search_button)

        vbox = QVBoxLayout()
        vbox.addStretch(1)
        vbox.addLayout(hbox)
        vbox.addStretch(1)
        vbox.addLayout(github_hbox)
        vbox.addStretch(1)
        vbox.addLayout(hbox2)
        vbox.addStretch(1)
        vbox.addLayout(hbox3)
        vbox.addStretch(1)
        vbox.addWidget(self.status_label)

        self.setLayout(vbox)

        self.setWindowTitle('Server SPY v1.1')
        self.setGeometry(300, 300, 700, 500)


class MyMain(MyMainGUI):
    add_sec_signal = pyqtSignal()
    send_instance_singal = pyqtSignal("PyQt_PyObject")

    def __init__(self, parent=None):
        super().__init__(parent)

        self.search_button.clicked.connect(self.search)
        self.add_button.clicked.connect(self.add)
        self.github_button.clicked.connect(lambda: webbrowser.open('https://github.com/Hydragon516/Server-SPY'))
        self.server_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.server_list.itemClicked.connect(self.chkItemClicked)

        self.th_search = searcher(parent=self)
        self.th_search.updated_list.connect(self.server_list_update)
        self.th_search.updated_label.connect(self.main_status_update)

        self.th_status = status_run(parent=self)
        self.th_status.updated_status.connect(self.status_bar_update)
        self.th_status.updated_label.connect(self.main_status_update)

        self.show()
    
    def add(self):
        ip = self.add_IP.text()
        id = self.add_ID.text()
        pw = self.add_PW.text()
        port = self.add_PORT.text()

        if ip == "" or id == "" or pw == "" or " " in ip or " " in id or " " in pw or " " in port:
            print(ip, id, pw, port)
            self.status_label.setText("서버 추가 실패! (빈칸이 있습니다.)")

        else:
            with open("server.txt", "a") as f:
                f.write("{},{},{},{}\n".format(ip, id, pw, port))
            f.close()
            self.status_label.setText("서버 추가 완료! (검색 버튼을 눌러주세요.)")

    @pyqtSlot()
    def chkItemClicked(self):
        global global_server_list
        global target_server

        try:
            self.th_status.terminate()
        except:
            pass
        
        server = self.server_list.selectedItems()
        server_idx = self.server_list.currentIndex().row()
        server_ip = server[0].text().split(' ')[0]

        try:
            id, pw, port = global_server_list[server_idx]
            target_server = (server_ip, id, pw, port)
        except:
            return

        if id == None or pw == None:
            self.status_label.setText("연결 불가능한 서버입니다.".format(id))
        
        else:
            self.th_status.start()
    
    @pyqtSlot()
    def search(self):
        self.cpu_bar.reset()
        self.mem_bar.reset()
        for i in range(len(self.gpu_bar)):
            self.gpu_bar[i].reset()

        self.th_status.terminate()
        self.server_list.clear()
        self.th_search.start()

    @pyqtSlot(str)
    def server_list_update(self, msg):
        if "Disconnected" in msg:
            msg = QListWidgetItem(msg)
            msg.setForeground(Qt.red)
        self.server_list.addItem(msg)

    @pyqtSlot(list)
    def status_bar_update(self, msg):
        self.cpu_bar.reset()
        self.mem_bar.reset()
        for i in range(len(self.gpu_bar)):
            self.gpu_bar[i].reset()

        cpu_usage = int(msg[0])
        mem_usage = float(msg[1])

        if cpu_usage >= 80:
            self.cpu_bar.setStyleSheet("QProgressBar::chunk {background-color: red}")
        elif cpu_usage >= 50:
            self.cpu_bar.setStyleSheet("QProgressBar::chunk {background-color: yellow}")
        else:
            self.cpu_bar.setStyleSheet("QProgressBar::chunk {background-color: green}")

        if mem_usage >= 80:
            self.mem_bar.setStyleSheet("QProgressBar::chunk {background-color: red}")
        elif mem_usage >= 50:
            self.mem_bar.setStyleSheet("QProgressBar::chunk {background-color: yellow}")
        else:
            self.mem_bar.setStyleSheet("QProgressBar::chunk {background-color: green}")

        self.cpu_bar.setValue(int(msg[0]))
        self.cpu_bar.setAlignment(Qt.AlignCenter)
        self.mem_bar.setValue(float(msg[1]))
        self.mem_bar.setAlignment(Qt.AlignCenter)

        for i in range(len(msg[2:])):
            gpu_usage = int(msg[2 + i][0])
            if gpu_usage >= 80:
                self.gpu_bar[i].setStyleSheet("QProgressBar::chunk {background-color: red}")
            elif gpu_usage >= 50:
                self.gpu_bar[i].setStyleSheet("QProgressBar::chunk {background-color: yellow}")
            else:
                self.gpu_bar[i].setStyleSheet("QProgressBar::chunk {background-color: green}")

            self.gpu_bar[i].setValue(int(msg[2 + i][0]))
            self.gpu_bar[i].setAlignment(Qt.AlignCenter)
            self.gpu_bar[i].setFormat("{} {}%".format(msg[2 + i][1], msg[2 + i][0]))

    
    @pyqtSlot(str)
    def main_status_update(self, msg):
        self.status_label.setText(msg)


class status_run(QThread):
    updated_status = pyqtSignal(list)
    updated_label = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__()
        self.main = parent

    def __del__(self):
        self.wait()
    
    def get_cpu_usage(self):
        stdin, stdout, stderr = self.cli.exec_command("echo $[100-$(vmstat 1 2|tail -1|awk '{print $15}')]")
        cpu = stdout.read().decode('utf-8').replace('\n', '')
        return cpu

    def get_mem_usage(self):
        stdin, stdout, stderr = self.cli.exec_command("free -m | awk 'NR==2{printf \"%.2f\", $3*100/$2 }'")
        mem = stdout.read().decode('utf-8').replace('\n', '')
        return mem
    
    def get_gpu_usage(self):
        # gpu usage
        stdin, stdout, stderr = self.cli.exec_command("nvidia-smi | grep % | awk '{print $13}'")

        gpu_usage = stdout.read().decode('utf-8').replace('\n', '')
        gpu_usage = gpu_usage.split('%')
        gpu_usage = gpu_usage[:-1]

        return gpu_usage
    
    def get_gpu_name(self, num_gpu):
        stdin, stdout, stderr = self.cli.exec_command("nvidia-smi -q")
        gpu_names = []
        gpu_info = stdout.read().decode('utf-8').replace('\n', '')
        for i in range(1, num_gpu + 1):
            gpu_name = str(((gpu_info.split('Product Name')[i]).split(':')[1]).split('Product Brand')[0])
            gpu_name = gpu_name.replace(' ', '').replace('NVIDIA', '')
            gpu_names.append(gpu_name)
        return gpu_names
    
    def run(self):
        global target_server

        server_id = target_server[1]
        self.updated_label.emit("{} 서버 연결 하는 중...".format(server_id))
        try:
            self.cli = paramiko.SSHClient()
            self.cli.set_missing_host_key_policy(paramiko.AutoAddPolicy)

            server_ip = target_server[0]
            server_id = target_server[1]
            server_pw = target_server[2]
            server_port = target_server[3]
            
            self.cli.connect(server_ip, port=server_port, username=server_id, password=server_pw)
            self.updated_label.emit("{} 서버 연결 완료!".format(server_id))

        except:
            self.updated_label.emit("{} 서버 연결 실패! [서버 재 검색을 시도하세요]".format(server_id))
            return

        self.updated_label.emit("{} 서버의 실시간 사용량을 불러오는 중...".format(server_id))
        while True:
            cpu_usage = self.get_cpu_usage()
            mem_usage = self.get_mem_usage()
            gpu_usage = self.get_gpu_usage()
            num_gpu = len(gpu_usage)
            gpu_name = self.get_gpu_name(num_gpu)

            msg = [cpu_usage, mem_usage]
            for i in range(len(gpu_usage)):
                msg.append((gpu_usage[i], gpu_name[i]))
            
            self.updated_label.emit("사용량 불러오기 완료!")

            self.updated_status.emit(msg)
    

class searcher(QThread):
    updated_list = pyqtSignal(str)
    updated_label = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__()
        self.main = parent

    def __del__(self):
        self.wait()

    def run(self):
        global global_server_list

        self.updated_list.emit("{:<35}{:<25}".format('IP', 'Name'))
        self.updated_label.emit("서버 검색 중...")

        ok_cnt = 0
        not_ok_cnt = 0

        with open("server.txt", "r") as f:
            server_idx = 0
            for line in f:
                line = line.replace('\n', '')
 
                server_ip = line.split(',')[0].replace(' ', '')
                server_id = line.split(',')[1].replace(' ', '')
                server_pw = line.split(',')[2].replace(' ', '')
                server_port = line.split(',')[3].replace(' ', '')
                server_port = int(server_port)

                server_idx += 1

                try:
                    cli = paramiko.SSHClient()
                    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy)
                    
                    cli.connect(server_ip, port=server_port, username=server_id, password=server_pw)
                    global_server_list[server_idx] = [server_id, server_pw, server_port]

                    self.updated_list.emit("{:<25}{:<25}".format(server_ip, server_id))
                    cli.close()
                    ok_cnt += 1

                except:
                    global_server_list[server_idx] = [None, None, None]
                    self.updated_list.emit("{:<25}{} [Disconnected]".format(server_ip, server_id))
                    not_ok_cnt += 1
        
        f.close()

        self.updated_label.emit("서버 검색 완료! : 연결 됨 {}개 / 연결 안됨 {}개".format(ok_cnt, not_ok_cnt))


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    form = MyMain()
    app.exec_()
