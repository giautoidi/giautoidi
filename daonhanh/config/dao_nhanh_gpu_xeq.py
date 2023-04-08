import os
import sys
import time
from sys import platform
import requests
import subprocess


if platform == "linux" or platform == "linux2":
    operate_system = 'lin'
elif platform == "darwin":
    operate_system = 'OS X'
elif platform == "win32":
    operate_system = 'win'

timeout = 30
thoi_gian_nghi = 28800

if operate_system == 'lin':
    try:
        os.system('apt-get update -y')
        #os.system ('apt --fix-broken install -y')
        os.system('apt-get install -y screen')
        os.system('apt-get install -y python-pip')
        os.system('apt-get install -y python3-pip')
    except:
        pass
    try:
        os.system('pip install psutil')
        os.system('pip3 install psutil')
    except:
        pass
import psutil
command_xmrig_default = '-c /opt/xmrig_linux/config.json'
while True:
    time.sleep(1)
    working_dir = os.path.dirname(os.path.realpath(__file__))
    print(working_dir)
    path_app = os.path.realpath(__file__)
    version_chinh = 5.0
    link_version_chinh = 'https://raw.githubusercontent.com/giautoidi/giautoidi/beta/daonhanh/version_chinh'
    link_dao = 'https://raw.githubusercontent.com/giautoidi/giautoidi/beta/daonhanh/dao_nhanh_gpu_xeq.py'
    try:
        response = requests.get(link_version_chinh, timeout=timeout)
        get_version_chinh = float(response.text)
        print(get_version_chinh)
        if get_version_chinh == version_chinh:
            print('Dang o version moi nhat la %s' % version_chinh)
        else:
            if len(response.text) < 5:
                print('Co version moi, update thoi')
                response = requests.get(link_dao, timeout=timeout)
                data_trave = response.text
                print(data_trave)
                fileopen = open(path_app, 'w+')
                fileopen.write(data_trave)
                fileopen.close()
                os.system('python3 %s' % path_app)
                sys.exit()
    except:
        pass
    
    if operate_system == 'lin':
        try:
            path_service = '/lib/systemd/system/dao.service'
            data = '[Unit]\nDescription=dao service\n[Service]\nType=simple\nExecStart=/usr/bin/python3 %s\n[Install]\nWantedBy=multi-user.target' % path_app
            if not os.path.exists(path_service):
                fileopen = open(path_service, 'w+')
                fileopen.write(data + '\n')
                fileopen.close()
            #os.system('chmod 600 %s' %path)
                os.system('systemctl daemon-reload')
                os.system('systemctl enable dao')
        except:
            pass
    #utopia
    if operate_system == 'lin':
        #xmrig_stak
        link_download_xmrig = 'https://github.com/fireice-uk/xmr-stak/releases/download/2.10.8/xmr-stak-linux-2.10.8-cpu_cuda-nvidia.tar.xz'
        gz_name = 'xmr-stak-linux-2.10.8-cpu_cuda-nvidia.tar.xz'
        folder_xmrig = 'xmr-stak-linux-2.10.8-cpu_cuda-nvidia'
        xmrig_name = 'xmr-stak'
        try:
            if not os.path.isfile('/opt/%s/%s' %(folder_xmrig, xmrig_name)):
                print('Chua co chuong trinh %s' %xmrig_name)
                os.chdir('/opt')
                os.system('rm -f /opt/%s' %gz_name)
                os.system('wget %s' %link_download_xmrig)
                os.system('tar xf %s' %gz_name)
                os.chdir('/opt/%s' %folder_xmrig)
                #workingdir = os.getcwd()
                os.system('chmod 777 %s' %xmrig_name)
                workingdir = os.getcwd()
                data_config = '"call_timeout" : 10,\n"retry_time" : 30,\n"giveup_limit" : 0,\n"verbose_level" : 4,\n"print_motd" : true,\n"h_print_time" : 300,\n"aes_override" : null,\n"use_slow_memory" : "warn",\n"tls_secure_algo" : true,\n"daemon_mode" : true,\n"output_file" : "",\n"httpd_port" : 0,\n"http_login" : "",\n"http_pass" : "",\n"prefer_ipv4" : true,\n'
                f = open("config.txt", "w")
                f.write(data_config)
                f.close()
                # os.system('wget %s' %link_config_nvidia_file)
                # os.system('wget %s' %link_pool_nvidia_file)
                data_pool = '"pool_list" :\n[\n\t{"pool_address" : "us.equilibria.herominers.com:1195", "wallet_address" : "Tsz55GU5hVbPZ3h86Ssi4NJSp6EKtNQ2XL8nxSmKn3zzPXHf81ks3CdcFNwXxskoRGbw1xzcrYHN27ANxa1uEi3m4M3WxecJat", "rig_id" : "", "pool_password" : "nql", "use_nicehash" : false, "use_tls" : false, "tls_fingerprint" : "", "pool_weight" : 1 },\n],\n"currency" : "cryptonight_gpu",\n'
                f = open("pools.txt", "w")
                f.write(data_pool)
                f.close()
            else:
                print('Da co chuong trinh %s' %xmrig_name)
        except:
            pass
    
        try:
            xmrig_stak_dachay = False
            for proc in psutil.process_iter():
                process_name = proc.as_dict(attrs=['pid', 'name', 'create_time'])
                #print(process_name['name'])
                if xmrig_name == process_name['name']:
                    print('Da co chuong trinh %s chay' %xmrig_name)
                    xmrig_stak_dachay = True
                    break
        except:
            pass
        if xmrig_stak_dachay == False:
            try:
                os.system('nvidia-smi')
            except:
                pass
            os.chdir('/opt/%s' %folder_xmrig)
            command = '/opt/%s/%s' %(folder_xmrig, xmrig_name)
            print(command)
            if os.path.isfile('/usr/bin/screen'):
                print('Co chuong trinh screen')
                os.system ('screen -dmS %s %s' %(xmrig_name, command))
            elif os.path.isfile('/usr/bin/nohup'):
                print('Co chuong trinh nohup')
                os.system ('nohup %s &' %command)
            else:
                os.system ('%s &' %command)
    time.sleep(thoi_gian_nghi)
