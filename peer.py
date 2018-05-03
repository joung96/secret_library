from Tkinter import *
from ttk import *
from enum import Enum
import socket
import thread
import time
import string

CHECKED_OUT = 0 
CHECKED_IN = 1

class ChatClient(Frame):
  
  def __init__(self, root, client_id):
    Frame.__init__(self, root)
    self.root = root
    self.name = str(client_id)
    self.draw_gui()
    self.server_socket = None
    self.server_status = 0
    self.buffsize = 1024
    self.peers = {}
    self.counter = 0
    self.books = {}
    self.book_database = {}
    self.current_request = None
    self.lock = thread.allocate_lock()
    dictionary = list(string.ascii_uppercase)
    for i in range(5):
      self.books[dictionary[i + (client_id - 1) * 5]] = CHECKED_IN
    self.view_bookshelf()
    self.server_port = str(8080 + client_id)
    self.server_ip = "127.0.0.1"
    self.handle_set_server()
    time.sleep(2)

    # if there are multiple clients
    if client_id != 1: 
      cursor_id = client_id - 1
      while cursor_id > 0:
        client_port = 8080 + cursor_id
        print("sending to:" + str(client_port))
        self.handle_add_client("127.0.0.1", client_port, True)
        cursor_id -= 1

  def draw_gui(self):
    self.root.title("Secret Library")
    
    parent_frame = Frame(self.root)
    parent_frame.grid(stick=E+W+N+S)
    
    logs = Frame(parent_frame)
    self.received_messages = Text(logs, bg="white", width=60, height=30, state=DISABLED)
    self.friends = Listbox(logs, bg="white", width=30, height=30)
    self.received_messages.grid(row=0, column=0, sticky=W+N+S, padx = (0,10))
    self.friends.grid(row=0, column=1, sticky=E+N+S)

    submit_text = Frame(parent_frame)
    self.message = StringVar()
    self.message_field = Entry(submit_text, width=20, textvariable=self.message)
    send_message = Button(submit_text, text="Request", width=10, command=self.handle_request)
    self.message_field.grid(row=0, column=0, sticky=W)
    send_message.grid(row=0, column=1, padx=5)

    view_shelf = Button(submit_text, text="View Bookshelf", width=15, command=self.view_bookshelf)
    view_shelf.grid(row=1, column=1, padx=5)

    self.statusLabel = Label(parent_frame)

    footer = Label(parent_frame, text="Secret Library")
    
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
      server_address = (self.server_ip.replace(' ',''), int(self.server_port.replace(' ','')))

      self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      self.server_socket.bind(server_address)
      self.server_socket.listen(5)
      self.status("Server listening on %s:%s" % server_address)
      thread.start_new_thread(self.client,())
      self.server_status = 1
      self.name = self.name.replace(' ','')
      if self.name == '':
          self.name = "%s:%s" % server_address
      self.log_message("me", "successfully set server address")
    except:
        print(sys.exc_info())
        self.status("Error in server bootstrap")
    
  def client(self):
    while 1:
      clientsoc, clientaddr = self.server_socket.accept()
      self.status("Client connected from %s:%s" % clientaddr)
      self.add_client(clientsoc, clientaddr)
      for client in self.peers.keys():
        client.send("SHELF:" + str(self.books.keys()))
      thread.start_new_thread(self.handle_client_message, (clientsoc, clientaddr))
    self.server_socket.close()

  def view_bookshelf(self): 
    checked_in = [] 
    for book, status in self.books.iteritems(): 
      if status == CHECKED_IN: 
        checked_in.append(book)
    self.log_message("my bookshelf", str(checked_in))
  
  def handle_add_client(self, client_ip, client_port, show_books):
    if self.server_status == 0:
      self.status("Set server address first")
      return None
    clientaddr = (client_ip, client_port)
    try:
        clientsoc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientsoc.connect(clientaddr)
        self.status("Connected to client on %s:%s" % clientaddr)
        self.add_client(clientsoc, clientaddr)
        if show_books:
          print("handle" +  str(self.books.keys()))
          for client in self.peers.keys():
            print("heya: " + str(client))
            client.send("SHELF:"  + str(self.books.keys()))
        thread.start_new_thread(self.handle_client_message, (clientsoc, clientaddr))

        return
    except:
        print(sys.exc_info())
        self.status("Error connecting to client")

  def handle_client_message(self, clientsoc, clientaddr):
    while 1:
      try:
        data = clientsoc.recv(self.buffsize)
        if not data:
            break
        if "REQUEST" in data: 
          book = data.split("REQUEST:")[1]
          message = None
          if book in self.books.keys():  
            message = "LEND:" + book
            self.books[book] = CHECKED_OUT
            for client in self.peers.keys():
              client.send(message)
            self.view_bookshelf()
        elif "LEND" in data: 
          book = data.split("LEND:")[1]
          for client, books in self.book_database.iteritems():
            if book in books[1]: 
              self.lock.acquire()
              lst = books[1]
              lst.remove(str(book))
              self.friends.delete(books[0])
              self.counter += 1
              self.friends.insert(self.counter, str(lst))
              self.book_database[client] = (self.counter, lst)
              self.lock.release()
          if book == self.current_request:
            self.books[book] = CHECKED_IN 
            self.view_bookshelf()
            self.current_request = None

        elif "SHELF" in data: 
          print("heya2" + str(clientaddr))
          shelf = self.string_to_list(data.split("SHELF:")[1])
          print(shelf)
          print(self.book_database[clientsoc])
          if self.book_database[clientsoc] != shelf:
            self.lock.acquire()
            self.counter += 1
            self.book_database[clientsoc] = (self.counter, shelf)
            self.friends.insert(self.counter, data.split("SHELF:")[1])
            print(self.book_database)
            self.lock.release()
        else:
          self.log_message("%s:%s" % clientaddr, data)
      except:
          print(sys.exc_info())
          break
    self.remove_client(clientsoc, clientaddr)
    clientsoc.close()
    self.status("Client disconnected from %s:%s" % clientaddr)

  def string_to_list(self, data):
    print("oh no")
    print(data) 
    lst_data = list(data)
    result = []
    letters = string.ascii_uppercase
    counter = 0
    while counter < len(lst_data): 
      if lst_data[counter] in letters: 
        result.append(str(lst_data[counter]))
      counter += 1
    return result
  
  def handle_request(self):
    if self.server_status == 0:
      self.status("Set server address first")
      return
    msg = self.message.get().replace(' ','')
    if msg == '':
        return
    self.log_message("me", msg)
    self.current_request = msg
    for client in self.peers.keys():
      client.send("REQUEST:" + msg)
  
  def handle_return(self): 
    if self.server_status == 0:
      self.status("Set server address first")
      return
    msg = self.message.get().replace(' ','')
    if msg == '':
        return
    self.log_message("me", msg)
    for client in self.peers.keys():
      client.send("REQUEST:" + msg)
      
  def log_message(self, client, msg):
    self.lock.acquire()
    self.received_messages.config(state=NORMAL)
    print("logging " + msg)
    self.received_messages.insert("end",client+": "+msg+"\n")
    self.received_messages.config(state=DISABLED)
    self.lock.release()
  
  def add_client(self, clientsoc, clientaddr):
    self.peers[clientsoc]=self.counter
    self.book_database[clientsoc]=None
    print(self.book_database)
  
  def remove_client(self, clientsoc, clientaddr):
    self.friends.delete(self.peers[clientsoc])
    del self.peers[clientsoc]
    del self.book_database[clientsoc]
  
  def status(self, msg):
    self.statusLabel.config(text=msg)
    print msg
      
def main(client_id):  
  root = Tk()
  ChatClient(root, client_id)
  root.mainloop()  

if __name__ == '__main__':
  if len(sys.argv) != 2 or int(sys.argv[1]) < 1: 
    print("ERROR: Usage 'python peer.py <client_id of at least 1>'")
    sys.exit()
  else:
    main(int(sys.argv[1]))  