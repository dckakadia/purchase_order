import paramiko

def run_ssh_command():
    host = '116.74.77.22'
    port = 22
    username = 'dckakadia'
    password = 'Devin@404404'
    
    command = "cd purchase_order && git pull origin main && sudo -S pm2 restart purchase_order"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(host, port, username, password, look_for_keys=False, allow_agent=False)
        stdin, stdout, stderr = ssh.exec_command(command)
        
        # provide password for sudo
        stdin.write(password + '\n')
        stdin.flush()
        
        out = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8')
        
        with open('ssh_output.txt', 'w', encoding='utf-8') as f:
            f.write(f"STDOUT:\n{out}\nSTDERR:\n{err}")
            
    except Exception as e:
        with open('ssh_output.txt', 'w', encoding='utf-8') as f:
            f.write(f"ERROR: {str(e)}")
    finally:
        ssh.close()

if __name__ == '__main__':
    run_ssh_command()
