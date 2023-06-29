from PyQt5.QtCore import pyqtSignal, pyqtSlot, QThread
from PyQt5.QtWidgets import QAbstractItemView, QLabel, QListWidget, QLineEdit, QDialog, QPushButton, QHBoxLayout, QVBoxLayout, QApplication
import paramiko

global_server_list = {}

target_server = None

class MyMainGUI(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.add_button = QPushButton("서버 추가")
        self.add_IP = QLineEdit(self)
        self.IP_label = QLabel("IP :", self)
        self.add_ID = QLineEdit(self)
        self.ID_label = QLabel("ID :", self)
        self.add_PW = QLineEdit(self)
        self.PW_label = QLabel("PW :", self)
        self.server_list = QListWidget(self)
        self.server_list.resize(600, 600)
        self.status_list = QListWidget(self)
        self.status_list.resize(600, 600)

        self.status_label = QLabel("", self)

        self.search_button = QPushButton("서버 (재)검색")

        hbox = QHBoxLayout()
        hbox.addStretch(0)
        hbox.addWidget(self.IP_label)
        hbox.addWidget(self.add_IP)
        hbox.addWidget(self.ID_label)
        hbox.addWidget(self.add_ID)
        hbox.addWidget(self.PW_label)
        hbox.addWidget(self.add_PW)
        hbox.addWidget(self.add_button)
        hbox.addStretch(0)

        hbox2 = QHBoxLayout()
        hbox2.addWidget(self.server_list)
        hbox2.addWidget(self.status_list)

        hbox3 = QHBoxLayout()
        hbox3.addWidget(self.search_button)

        vbox = QVBoxLayout()
        vbox.addStretch(1)
        vbox.addLayout(hbox)
        vbox.addStretch(1)
        vbox.addLayout(hbox2)
        vbox.addStretch(1)
        vbox.addLayout(hbox3)
        vbox.addStretch(1)
        vbox.addWidget(self.status_label)

        self.setLayout(vbox)

        self.setWindowTitle('Server SPY v1.0')
        self.setGeometry(300, 300, 500, 400)


class MyMain(MyMainGUI):
    add_sec_signal = pyqtSignal()
    send_instance_singal = pyqtSignal("PyQt_PyObject")

    def __init__(self, parent=None):
        super().__init__(parent)

        self.search_button.clicked.connect(self.search)
        self.add_button.clicked.connect(self.add)
        self.server_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.server_list.itemClicked.connect(self.chkItemClicked)

        self.th_search = searcher(parent=self)
        self.th_search.updated_list.connect(self.server_list_update)
        self.th_search.updated_label.connect(self.main_status_update)

        self.th_status = status_run(parent=self)
        self.th_status.updated_list.connect(self.status_list_update)



        self.show()
    
    def add(self):
        ip = self.add_IP.text()
        id = self.add_ID.text()
        pw = self.add_PW.text()

        if ip == "" or id == "" or pw == "" or " " in ip or " " in id or " " in pw: 
            self.status_label.setText("서버 추가 실패! (빈칸이 있습니다.)")

        else:
            with open("server.txt", "a") as f:
                f.write("{},{},{}\n".format(ip, id, pw))
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
        server_ip = server[0].text().split(' ')[0]
        id, pw = global_server_list[server_ip]
        target_server = (server_ip, id, pw)

        if id == None or pw == None:
            self.status_list.clear()
        
        else:
            self.status_list.clear()
            self.th_status.start()
    
    @pyqtSlot()
    def search(self):
        self.server_list.clear()
        self.th_search.start()

    @pyqtSlot(str)
    def server_list_update(self, msg):
        self.server_list.addItem(msg)

    @pyqtSlot(str)
    def status_list_update(self, msg):
        self.status_list.clear()
        self.status_list.addItem(msg)
    
    @pyqtSlot(str)
    def main_status_update(self, msg):
        self.status_label.setText(msg)


class status_run(QThread):
    updated_list = pyqtSignal(str)
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

        return gpu_usage
    
    def run(self):
        global target_server

        try:
            self.cli = paramiko.SSHClient()
            self.cli.set_missing_host_key_policy(paramiko.AutoAddPolicy)

            server_ip = target_server[0]
            server_id = target_server[1]
            server_pw = target_server[2]
            
            self.cli.connect(server_ip, port=22, username=server_id, password=server_pw)

        except:
            return

        while True:
            cpu_usage = self.get_cpu_usage()
            mem_usage = self.get_mem_usage()
            gpu_usage = self.get_gpu_usage()


            cpu_label = "CPU 사용량 : {}%".format(cpu_usage)
            mem_label = "MEM 사용량 : {}%".format(mem_usage)
            gpu_label = ""

            for i in range(len(gpu_usage)-1):
                gpu_label += "GPU {} : {}%\n".format(i, gpu_usage[i])

            self.updated_list.emit(cpu_label + "\n" + mem_label + "\n" + gpu_label)

            # self.main.status_label.setText("CPU 사용량 : {}%".format(cpu_usage))
    

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

        with open("server.txt", "r") as f:
            for line in f:
                line = line.replace('\n', '')

                server_ip = line.split(',')[0].replace(' ', '')
                server_id = line.split(',')[1].replace(' ', '')
                server_pw = line.split(',')[2].replace(' ', '')

                try:
                    cli = paramiko.SSHClient()
                    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy)
                    
                    cli.connect(server_ip, port=22, username=server_id, password=server_pw)
                    global_server_list[server_ip] = [server_id, server_pw]

                    self.updated_list.emit("{:<25}{:<25}".format(server_ip, server_id))

                except:
                    global_server_list[server_ip] = [None, None]
                    self.updated_list.emit("{:<25}{:<25}".format(server_ip, server_id))
        
        f.close()

        self.updated_label.emit("서버 검색 완료!")


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    form = MyMain()
    app.exec_()