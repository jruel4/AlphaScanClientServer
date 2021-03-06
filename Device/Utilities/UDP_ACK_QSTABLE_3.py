# -*- coding: utf-8 -*-
"""
Created on Sun Feb 05 23:56:43 2017

@author: marzipan
"""

# -*- coding: utf-8 -*-
"""
Created on Sun Feb 05 17:51:48 2017

@author: marzipan
"""

# -*- coding: utf-8 -*-
"""
Created on Sun Jan 24 12:12:43 2016

@author: marzipan
"""

import socket
import time
from collections import deque
import matplotlib.pyplot as plt

UDP_IP = "192.168.1.227"
UDP_PORT = 50007
MESSAGE = 'xxx'
BUF_MAX = 1400*8
RCV_TMO = 0.006

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,BUF_MAX)
sock.bind(('',UDP_PORT))
sock.sendto(MESSAGE, (UDP_IP, UDP_PORT))

#socket.setdefaulttimeout(0)
#sock.setblocking(False)

# Increase this to minimize bandwidth usage, decrease to minimize latency
sock.settimeout(RCV_TMO)
# This should balance with timeout to equal tx rate 
ERR_THRESH = 2

data = ''
inbuf = list()
errors = 0
t_errors = 0
t_errsnd = 0

# track the longest delay between fresh packets
max_delay = 0
delay_list = list()
tb = time.time()

# Track the throughput per second
rx_buf = deque([(0,0) for i in range(100)],100)
prev_ctr = -2
Bps_list = list()
t0 = time.time()

# Track synchronization
resend_count = 0
RESEND_THRESH = 6
SYNC_TOKEN = chr(0x1)
NOSYNC_TOKEN = chr(0x0)
SYNC_FLAG = NOSYNC_TOKEN
ctr = 0

def flush_UDP(sock):
    try:
        sock.settimeout(0)
        sock.recv(BUF_MAX)
    except:
        pass
    sock.settimeout(RCV_TMO)
    
def get_newest_ctr(sock):
    valid = 0
    nctr = -1
    while 1:
        try:
            data = sock.recv(1400)
            nctr = ord(data[0])
            valid = len(data)
        except:
            return nctr,valid

while True:
    try:
        if (errors > ERR_THRESH):
            # This implies that remote hasn't sent another packet, so resend ACK
            MESSAGE = chr(ctr)+'_'.encode('utf-8')+SYNC_FLAG
            sock.sendto(MESSAGE, (UDP_IP, UDP_PORT))
            time.sleep(0.005)
            errors = 0
            resend_count += 1
            t_errsnd += 1
            
        # Receive packet
        nctr,size = get_newest_ctr(sock)
        if (size): 
            ctr = nctr
        else:
            raise Exception()
        #print(ctr)
        
        # Append new data
        if ctr != prev_ctr:
            resend_count = 0
            errors = 0
            SYNC_FLAG = NOSYNC_TOKEN
            rx_buf.append((time.time(), size))
            prev_ctr = ctr
            # Check if new max delay reached
            tn = time.time()
            td = (tn - tb)
            if td > max_delay:
                max_delay = td
            tb = tn
            delay_list += [(tn-t0, td)]
            
            # print rx rate
            if ctr == 0:
                t = 0
                for d in rx_buf:
                    t += d[1]
                Bps = t/(rx_buf[-1][0] - rx_buf[0][0])
                Bps_list += [(tn-t0,Bps)]
                print("Bps: ", tn-t0, Bps, max_delay)
        else:
            # If new ctr does == previous then we track it to monitor synchronization
            resend_count += 1
            # If resend exceed threshold then trigger sync event
            if resend_count > RESEND_THRESH:
                # Perform sync
                nctr,valid = get_newest_ctr(sock)
                if valid: ctr = nctr
                print("Sync")                
                MESSAGE = chr(ctr)+'_'.encode('utf-8')+SYNC_TOKEN
                sock.sendto(MESSAGE, (UDP_IP, UDP_PORT))
                time.sleep(0.005)
                data = sock.recv(1400)
                nctr = ord(data[0])
                
                while nctr != ((ctr+1)%256):
                    ctr = nctr
                    flush_UDP(sock) # Shouldnt have anything in buffer since previous flush... but could call 
                    MESSAGE = chr(ctr)+'_'.encode('utf-8')+SYNC_TOKEN
                    sock.sendto(MESSAGE, (UDP_IP, UDP_PORT))
                    time.sleep(0.005) #TODO make this longer?
                    data = sock.recv(1400)
                    nctr = ord(data[0])
                    
                ctr = nctr
                resend_count = 0
                #TODO flush_UDP(sock)
                #errors = 0
                
                continue
            
        # Send ACK for received data
        MESSAGE = chr(ctr)+'_'.encode('utf-8')+NOSYNC_TOKEN
        sock.sendto(MESSAGE, (UDP_IP, UDP_PORT))
        errors = 0
    except KeyboardInterrupt:
        break
    except:
        errors += 1
        t_errors += 1
        
sock.close()

def plot_delay():# input delay list
    global delay_list
    t = [u[0] for u in delay_list]
    v = [u[1] for u in delay_list]
    plt.plot(t,v)
    plt.show()

def plot_Bps():
    global Bps_list
    t = [u[0] for u in Bps_list]
    v = [u[1] for u in Bps_list]
    plt.plot(t,v)
    plt.show()

plot_delay()




