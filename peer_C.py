from Tkinter import *
from ttk import *
import socket
import thread

class ChatClient(Frame):
  
  def __init__(self, root):
    Frame.__init__(self, root)
    self.root = root
    self.draw_gui()
    self.server_socket = None
    self.server_status = 0
    self.buffsize = 1024
    self.peers = {}
    self.counter = 0
    self.books = ["K", "L", "M", "N", "O"]

    self.log_message("bookshelf", str(self.books))
  
  def draw_gui(self):
    self.root.title("Secret Library")
    
    parent_frame = Frame(self.root)
    parent_frame.grid(stick=E+W+N+S)
    
    main_window = Frame(parent_frame)
    server_name = Label(main_window, text="Set: ")
    self.name = StringVar()
    self.name.set("name")
    name_field = Entry(main_window, width=10, textvariable=self.name)
    self.server_ip = StringVar()
    self.server_ip.set("127.0.0.1")
    server_ip_field = Entry(main_window, width=15, textvariable=self.server_ip)
    self.server_port = StringVar()
    self.server_port.set("8090")
    server_port_field = Entry(main_window, width=5, textvariable=self.server_port)
    server_set = Button(main_window, text="Set", width=10, command=self.handle_set_server)
    add_client = Label(main_window, text="Add peer: ")
    self.client_ip = StringVar()
    self.client_ip.set("127.0.0.1")
    client_ip_field = Entry(main_window, width=15, textvariable=self.client_ip)
    self.client_port = StringVar()
    self.client_port.set("8091")
    client_port_field = Entry(main_window, width=5, textvariable=self.client_port)
    client_set = Button(main_window, text="Add", width=10, command=self.handle_add_client)
    server_name.grid(row=0, column=0)
    name_field.grid(row=0, column=1)
    server_ip_field.grid(row=0, column=2)
    server_port_field.grid(row=0, column=3)
    server_set.grid(row=0, column=4, padx=5)
    add_client.grid(row=0, column=5)
    client_ip_field.grid(row=0, column=6)
    client_port_field.grid(row=0, column=7)
    client_set.grid(row=0, column=8, padx=5)
    

    logs = Frame(parent_frame)
    self.received_messages = Text(logs, bg="white", width=60, height=30, state=DISABLED)
    self.friends = Listbox(logs, bg="white", width=30, height=30)
    self.received_messages.grid(row=0, column=0, sticky=W+N+S, padx = (0,10))
    self.friends.grid(row=0, column=1, sticky=E+N+S)

    submit_text = Frame(parent_frame)
    self.message = StringVar()
    self.message_field = Entry(submit_text, width=20, textvariable=self.message)
    send_message = Button(submit_text, text="Request", width=10, command=self.handle_send)
    self.message_field.grid(row=0, column=0, sticky=W)
    send_message.grid(row=0, column=1, padx=5)

    send_message2 = Button(submit_text, text="Return", width=10, command=self.handle_send)
    send_message2.grid(row=0, column=2, padx=5)

    send_message2 = Button(submit_text, text="Browse", width=10, command=self.handle_send)
    send_message2.grid(row=1, column=1, padx=5)


    self.statusLabel = Label(parent_frame)

    footer = Label(parent_frame, text="Secret Library")
    
    main_window.grid(row=0, column=0)
    logs.grid(row=1, column=0)
    submit_text.grid(row=2, column=0, pady=10)
    self.statusLabel.grid(row=3, column=0)
    footer.grid(row=4, column=0, pady=10)
    
  def handle_set_server(self):
    try:
      if self.server_socket != None:
        self.server_socket.close()
        self.server_socket = None
        self.server_status = 0
      server_address = (self.server_ip.get().replace(' ',''), int(self.server_port.get().replace(' ','')))

      self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      self.server_socket.bind(server_address)
      self.server_socket.listen(5)
      self.status("Server listening on %s:%s" % server_address)
      thread.start_new_thread(self.client,())
      self.server_status = 1
      self.name = self.name.get().replace(' ','')
      if self.name == '':
          self.name = "%s:%s" % server_address
    except:
        print(sys.exc_info())
        self.status("Error in server bootstrap")
    
  def client(self):
    while 1:
      clientsoc, clientaddr = self.server_socket.accept()
      self.status("Client connected from %s:%s" % clientaddr)
      self.add_client(clientsoc, clientaddr)
      thread.start_new_thread(self.handle_client_message, (clientsoc, clientaddr))
    self.server_socket.close()
  
  def handle_add_client(self):
    if self.server_status == 0:
      self.status("Set server address first")
      return
    clientaddr = (self.client_ip.get().replace(' ',''), int(self.client_port.get().replace(' ','')))
    try:
        clientsoc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientsoc.connect(clientaddr)
        self.status("Connected to client on %s:%s" % clientaddr)
        self.add_client(clientsoc, clientaddr)
        thread.start_new_thread(self.handle_client_message, (clientsoc, clientaddr))
    except:
        print(sys.exc_info())
        self.status("Error connecting to client")

  def handle_client_message(self, clientsoc, clientaddr):
    while 1:
      try:
        data = clientsoc.recv(self.buffsize)
        if not data:
            break
        self.log_message("%s:%s" % clientaddr, data)
      except:
          print(sys.exc_info())
          break
    self.remove_client(clientsoc, clientaddr)
    clientsoc.close()
    self.status("Client disconnected from %s:%s" % clientaddr)
  
  def handle_send(self):
    if self.server_status == 0:
      self.status("Set server address first")
      return
    msg = self.message.get().replace(' ','')
    if msg == '':
        return
    self.log_message("me", msg)
    for client in self.peers.keys():
      client.send(msg)
  
  def log_message(self, client, msg):
    self.received_messages.config(state=NORMAL)
    self.received_messages.insert("end",client+": "+msg+"\n")
    self.received_messages.config(state=DISABLED)
  
  def add_client(self, clientsoc, clientaddr):
    self.peers[clientsoc]=self.counter
    self.counter += 1
    self.peers.insert(self.counter,"%s:%s" % clientaddr)
  
  def remove_client(self, clientsoc, clientaddr):
      print self.peers
      self.peers.delete(self.peers[clientsoc])
      del self.peers[clientsoc]
      print self.peers
  
  def status(self, msg):
    self.statusLabel.config(text=msg)
    print msg
      
def main():  
  root = Tk()
  ChatClient(root)
  root.mainloop()  

if __name__ == '__main__':
  main()  