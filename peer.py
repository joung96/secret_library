from Tkinter import *
from ttk import *
import socket
import thread
import time
import string

CHECKED_OUT = 0 
CHECKED_IN = 1

class Library(Frame):
  
  def __init__(self, root, client_id):
    # bootstrap node
    Frame.__init__(self, root)
    self.root = root
    self.name = str(client_id)
    self.draw_gui()
    self.server_socket = None
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

    # server setup
    self.server_port = str(8080 + client_id)
    self.server_ip = socket.gethostname()

    try:
      server_address = (self.server_ip, int(self.server_port))
      self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      self.server_socket.bind(server_address)
      self.server_socket.listen(5)
      thread.start_new_thread(self.client,())
    except:
        print(sys.exc_info())

    # if there are multiple clients
    if client_id != 1: 
      cursor_id = client_id - 1
      while cursor_id > 0:
        client_port = 8080 + cursor_id
        print("sending to:" + str(client_port))
        self.handle_add_client(client_port, True)
        cursor_id -= 1

    self.friends.insert(END, "MY FRIENDS' BOOKS")

  def draw_gui(self):
    self.root.title("Secret Library")
    
    parent_frame = Frame(self.root)
    parent_frame.grid()
    
    logs = Frame(parent_frame)
    self.received_messages = Text(logs, bg="white", width=60, height=30, state=DISABLED)
    self.friends = Listbox(logs, bg="white", width=30, height=20)
    self.received_messages.grid(row=0, column=0, padx = (0,10))
    self.friends.grid(row=0, column=1)

    submit_text = Frame(parent_frame)
    self.message = StringVar()
    self.message_field = Entry(submit_text, width=20, textvariable=self.message)
    send_message = Button(submit_text, text="Request", width=10, command=self.handle_request)
    self.message_field.grid(row=0, column=0)
    send_message.grid(row=0, column=1, padx=5)

    submit_text2 = Frame(parent_frame)
    self.new_book = StringVar()
    self.new_book_field = Entry(submit_text2, width=20, textvariable=self.new_book)
    send_new_book = Button(submit_text2, text="Add Book", width=10, command=self.handle_add_book)
    self.new_book_field.grid(row=1, column=0)
    send_new_book.grid(row=1, column=1, padx=5)
    
    logs.grid(row=1, column=0)
    submit_text.grid(row=2, column=0, pady=10)
    submit_text2.grid(row=3, column=0, pady=10)

  def client(self):
    while 1:
      clientsoc, clientaddr = self.server_socket.accept()
      self.add_client(clientsoc, clientaddr)
      for client in self.peers.keys():
        client.send("SHELF:" + str(self.get_checked_in_books()))
      thread.start_new_thread(self.handle_client_message, (clientsoc, clientaddr))
    self.server_socket.close()

  def view_bookshelf(self): 
    self.log_message("my bookshelf", str(self.get_checked_in_books()))

  def get_checked_in_books(self): 
    checked_in = [] 
    for book, status in self.books.iteritems():  
      if status == CHECKED_IN: 
        checked_in.append(book) 
    return checked_in

  def handle_add_book(self):
    msg = self.new_book.get().upper().strip()
    if len(msg) == 1:
      self.log_message("added new book", msg)
      self.lock.acquire()
      self.books[msg] = CHECKED_IN
      for client in self.peers.keys():
          client.send("SHELF:" + str(self.get_checked_in_books()))
      self.lock.release()
      self.view_bookshelf()
    else: 
      self.log_message("ERROR", "book title length must be 1")
    
  def handle_add_client(self, client_port, show_books):
    clientaddr = (socket.gethostname(), client_port)
    try:
        clientsoc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientsoc.connect(clientaddr)
        self.add_client(clientsoc, clientaddr)
        if show_books:
          for client in self.peers.keys():
            client.send("SHELF:"  + str(self.get_checked_in_books()))
        thread.start_new_thread(self.handle_client_message, (clientsoc, clientaddr))
        return
    except:
        print(sys.exc_info())

  def handle_client_message(self, clientsoc, clientaddr):
    while 1:
      try:
        data = clientsoc.recv(1024)
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
          self.lock.acquire()
          for client, books in self.book_database.iteritems():
            if book in books[1]: 
              lst = books[1]
              lst.remove(book)
              self.friends.delete(books[0])
              self.friends.insert(books[0], str(lst))
              self.book_database[client] = (books[0], lst)
          self.lock.release()
          if book == self.current_request:
            self.books[book] = CHECKED_IN 
            self.view_bookshelf()
            self.current_request = None
            for client in self.peers.keys():
              client.send("SHELF:"  + str(self.get_checked_in_books()))
        elif "SHELF" in data: 
          self.lock.acquire()
          shelf = self.string_to_list(data.split("SHELF:")[1])
          if not self.book_database[clientsoc] or self.book_database[clientsoc][1] != shelf:
            if self.book_database[clientsoc] != None:
              self.friends.delete(self.book_database[clientsoc][0])
              self.friends.insert(self.book_database[clientsoc][0], str(shelf))
              self.book_database[clientsoc] = (self.book_database[clientsoc][0], shelf)
              self.lock.release()
              continue
            self.counter += 1
            self.friends.insert(self.counter, data.split("SHELF:")[1])
            self.book_database[clientsoc] = (self.counter, shelf)
          self.lock.release()
      except:
          print(sys.exc_info())
          break
    self.remove_client(clientsoc, clientaddr)
    clientsoc.close()

  def string_to_list(self, data):
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
    msg = self.message.get().upper().strip()
    if len(msg) ==  1:
      self.log_message("requested", msg)
      self.current_request = msg
      for client in self.peers.keys():
        client.send("REQUEST:" + msg)
    else: 
      self.log_message("ERROR", "book title length must be 1")
      
  def log_message(self, client, msg):
    self.lock.acquire()
    self.received_messages.config(state=NORMAL)
    self.received_messages.insert("end",client+": "+msg+"\n")
    self.received_messages.config(state=DISABLED)
    self.lock.release()
  
  def add_client(self, clientsoc, clientaddr):
    self.peers[clientsoc]=None
    self.book_database[clientsoc]=None
  
  def remove_client(self, clientsoc, clientaddr):
    self.friends.delete(self.book_database[clientsoc][0])
    del self.peers[clientsoc]
    del self.book_database[clientsoc]
  
def main(client_id):  
  root = Tk()
  Library(root, client_id)
  root.mainloop()  

if __name__ == '__main__':
  if len(sys.argv) != 2 or int(sys.argv[1]) < 1: 
    print("ERROR: Usage 'python peer.py <client_id of at least 1>'")
    sys.exit()
  else:
    main(int(sys.argv[1]))  
