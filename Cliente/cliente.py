import socket
import selectors
import types
from tkinter import *
import struct
import threading
import hashlib
import queue


class GLOBALES:
    handShakeCliente = False
    handShakeServidor = False
    tamannoArchivo = 0
    nombreArchivo = ""
    HOST = ''
    PORT = 0
    f = open('./archivos/default.txt', 'wb')
    sel = selectors.DefaultSelector()
    received = False


cola = queue.Queue()


def start_connections(host, port, num_conns):
    server_addr = (host, port)
    for i in range(0, num_conns):
        connid = i + 1
        print('starting connection', connid, 'to', server_addr)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        sock.connect_ex(server_addr)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        data = types.SimpleNamespace(connid=connid,
                                     recv_total=0,
                                     outb=b'')
        GLOBALES.sel.register(sock, events, data=data)
        GLOBALES.handShakeCliente = False
        GLOBALES.handShakeServidor = False
        GLOBALES.received = False
        GLOBALES.tamannoArchivo = 0


def validarHash(hashServidor):
    GLOBALES.f.seek(0)
    return hashServidor == hashlib.sha1(GLOBALES.f.read()).digest()


def service_connection(key, mask):
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        #print("Reading...")
        recv_data = sock.recv(4096)  # Should be ready to read
        if recv_data and b'hash' not in recv_data and recv_data != b'End' and GLOBALES.handShakeServidor and GLOBALES.tamannoArchivo != 0:
            print('received', repr(recv_data), 'from connection', data.connid)
            data.recv_total += (len(recv_data))/4096
            GLOBALES.f.write(recv_data)
        elif recv_data == b'HandShake':
            print('received', repr(recv_data), 'from connection', data.connid)
            GLOBALES.handShakeServidor = True
            data.outb = b'HandShakeReceived'
        elif b'nombre' in recv_data or b'tamanno:' in recv_data:
            print('received', repr(recv_data), 'from connection', data.connid)
            indexComa = recv_data.find(b',')
            GLOBALES.tamannoArchivo = float(str(struct.unpack('f',recv_data[indexComa+9:])).split(",")[0][1:])
            GLOBALES.nombreArchivo = recv_data[7: indexComa].decode('utf-8')
            GLOBALES.f = open('./archivos/'+GLOBALES.nombreArchivo, 'wb+')
        elif b'hash' in recv_data:
            hashServidor = recv_data[5:]
            if validarHash(hashServidor):
                data.outb = b'Hashed'
            else:
                data.outb = b'WrongHashed'
            GLOBALES.f.close()
        if GLOBALES.received is not True and GLOBALES.tamannoArchivo != 0 and GLOBALES.tamannoArchivo < data.recv_total+0.5:
            data.outb = b'End'
            GLOBALES.received = True
        if not recv_data:
            print('closing connection', data.connid)
            GLOBALES.sel.unregister(sock)
            sock.close()
    if mask & selectors.EVENT_WRITE:
        if not data.outb and GLOBALES.handShakeCliente is not True:
            data.outb = b'HandShake'
            GLOBALES.handShakeCliente = True
        if data.outb:
            print('sending', repr(data.outb), 'to connection', data.connid)
            sent = sock.send(data.outb)  # Should be ready to write
            data.outb = data.outb[sent:]


def procesar():
    while True:
        try:
            events = GLOBALES.sel.select(timeout=None)
            for key, mask in events:
                if key.data is not None:
                    service_connection(key, mask)
        except Exception as e:
            print("Se Recibieron todos los datos")
            cola.put('Listo')
            print(e)
            break


raiz = Tk()
raiz.title("Cliente")
raiz.resizable(0, 0)
raiz.geometry("400x200")
estado = StringVar()
estado.set("Estado de la conexión: Desconectado")
estadoEnvio = StringVar()
estadoEnvio.set("Estado del Envio: Desconectado")
textEstado = Label(raiz, textvariable=estado).place(x=10, y=60)
lblEstadoEnvio = Label(raiz, textvariable=estadoEnvio).place(x=10, y=100)


class Thread(threading.Thread):
    def __init__(self, num, col):
        threading.Thread.__init__(self)
        self.num = num
        self.cola = col

    def run(self):
        procesar()
        sys.stdout.write("Hilo %d\n" % self.num)

def enviarNotificacion():
    t = Thread(1, cola)
    t.daemon = True
    t.start()
    estado.set("Estado de la conexión: Listo")
    estadoEnvio.set("Estado del Envio: Recibiendo...")
    botonListo.config(state=DISABLED)


botonListo = Button(raiz, text="Listo", command=enviarNotificacion)
botonListo.config(state=DISABLED)
botonListo.pack(side="bottom")


def ventanaConnect():
    ventanaConnect = Toplevel()
    ventanaConnect.title("Conectarse")
    ventanaConnect.resizable(0, 0)

    def connect():
        GLOBALES.HOST = '127.0.0.1'
        GLOBALES.PORT = 65432
        ventanaConnect.destroy()
        start_connections(GLOBALES.HOST, GLOBALES.PORT, 1)
        estado.set("Estado de la conexión: Conectado")
        estadoEnvio.set("Estado del Envio: No Recibido")
        botonListo.config(state='normal')
        boton1.config(state=DISABLED)

    host = StringVar()
    port = StringVar()
    hostLabel = Label(ventanaConnect, text="Ingresa el host del servidor").place(x=10, y=10)
    hostEntry = Entry(ventanaConnect, textvariable=host).place(x=180, y=10)
    portLabel = Label(ventanaConnect, text="Ingresa el puerto del servidor").place(x=10, y=40)
    portEntry = Entry(ventanaConnect, textvariable=port).place(x=180, y=40)
    botonConectar = Button(ventanaConnect, text="Conectar", command=connect)
    botonConectar.pack(side="bottom")
    ventanaConnect.geometry("320x100")


boton1 = Button(raiz, text="Conectarse", command=ventanaConnect)
boton1.place(x=10, y=0)
boton1.config(state='normal')

while True:
    raiz.update_idletasks()
    raiz.update()
    if cola.empty() is not True:
        cola.get()
        estado.set("Estado de la conexión: Desconectado")
        estadoEnvio.set("Estado del Envio: Recibido")
        boton1.config(state='normal')
