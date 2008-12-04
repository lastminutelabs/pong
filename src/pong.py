# Pong - works on N95 with aXYZ

import e32
import appuifw
import sensor
import axyz
import math
import audio
import socket
import sysinfo
import random
import traceback
import graphics
import math
import sys
import lightblue
import struct


# Misty is noce to remove the screensave but we're OK without it
try:
    __import__('misty')
except:
    pass

VERSION=0.2

# Store the phones that we know about . . .
PHONES = [("Russ N95", "00:18:42:E7:1B:6B"),
          ("Conor N95", "00:1E:3A:25:16:8B"),
          ("Labs N95", "00:1F:00:AE:54:0C")]

# Get their names etc
PHONE_NAMES = [unicode(n) for n, a in PHONES]
PHONE_ADDRESSES = [a for n, a in PHONES]

BT_SERVICE_NAME = u"phone pong - v%d"%VERSION
BT_CHANNEL=5

# The time each loop through the game loop will take
TICK_TIME=0.02

# The higher, the more sensitive
SENSITIVITY=35

# The different states of the game
GAME_STATE_MENU, GAME_STATE_STARTING, GAME_STATE_PLAYING = range(3)
accel_x=0
accel_y=0

# The size of the funny angled corners bit of the bat (in px)
BAT_CORNER_SIZE=10
BAT_CORNER_EFFECT=0.5 # (about 30 degrees in radians)

INITIAL_SPEED=6
SPEED_INCREASE=2

class Vector:
    def __init__(self, x=0, y=0):
        self.x=x
        self.y=y
    
    def dot(self, v2):
        return self.x*v2.x + self.y+v2.y

    # 0 degrees is vertical, going clockwise.
    def from_av(self, ang, velocity=1):
        self.x=-math.sin(-ang) * velocity
        self.y=-math.cos(-ang) * velocity
        
    def reflect_v(self):
        self.y=-self.y
    
    def reflect_h(self):
        self.x=-self.x
        
    def get_mag(self):
        return math.sqrt(self.x**2 + self.y**2)            

    def set_ang(self, ang):
        self.from_av(ang, self.get_mag())

    def add_mag(self, mag):
        ang=math.atan(self.x/self.y)
        if self.x>0 and self.y>0:
            ang=math.pi-ang
        elif self.x<0 and self.y>0:
            ang=math.pi+ang
        elif self.x<0 and self.y<0:
            ang=-ang
        self.x+=mag*math.cos(ang)
        self.y+=mag*math.sin(ang)

class Ponger:
    def __init__(self):
        self.x=0
        self.velocity=0
        self.acceleration=0
        self.width=50
        self.height=5
        self.y=5
        self.push_force=0
        
    def render(self, buffer):

        x1=self.x-self.width/2
        x2=x1+BAT_CORNER_SIZE
        x4=self.x+self.width/2
        x3=x4-BAT_CORNER_SIZE
        
        y2=self.y-self.push_force
        y1=self.y-self.height-self.push_force
        
        buffer.rectangle((x1,y1,x2,y2), fill=(204,204,255))
        buffer.rectangle((x2,y1,x3,y2), fill=(255,255,255))
        buffer.rectangle((x3,y1,x4,y2), fill=(204,204,255))

class Ball:
    def __init__(self):
        self.x=0
        self.y=0
        self.velocity=Vector()
        self.size=5 # (Half the size it renders at)
        
    def render(self, buffer):
        position=(self.x-self.size, self.y-self.size, self.x+self.size, self.y+self.size)
        buffer.rectangle(position, fill=(255,255,255) )





def handle_quit():
    global quit
    global game_state
    global app_lock
    if GAME_STATE_MENU==game_state:
        app_lock.signal()
    else:
        img.clear((0,0,0))
        handle_redraw()
        quit=True

def handle_event(event):
    handle_redraw(None)
    
def handle_redraw(rect=None):
    global img
    if img:
        canvas.blit(img)

def read_xyz(x, y, z):
    global accel_x
    global accel_y
    accel_x=x
    accel_y=y

def animate():
    global accel_x
    global accel_y

    # Deal with the accelerometer
    ponger.velocity=accel_y*SENSITIVITY
    if accel_x>30 and ponger.push_force<=0:
        if accel_x>50:
            accel_x=50
        ponger.push_force=accel_x/2

    # Animate the ponger
    ponger.x += ponger.velocity*TICK_TIME
    
    if ponger.push_force>0:
        ponger.push_force-=TICK_TIME*50
    else:
        ponger.push_force=0

    # Animate the ball
    ball.x+=ball.velocity.x
    ball.y+=ball.velocity.y
    
    # Speed up slowly over time
    ball.velocity.add_mag(TICK_TIME*SPEED_INCREASE)

def validate():   
    global quit
    global sync_counter
    
    w,h=canvas.size
    
    # ponger LHS
    w2=ponger.width/2
    if ponger.x-w2 < 0:
        ponger.x=w2
        ponger.velocity=0
        
    # ponger RHS
    elif ponger.x+w2 > w:
        ponger.x=w-w2
        ponger.velocity=0
        
    # Bounce the ball off the edges
    if ball.x<ball.size or ball.x>w-ball.size:
        ball.velocity.reflect_h()
    elif ball.y<ball.size+10 or ball.y>h-ball.size:
        ball.velocity.reflect_v()

    # Deal with ball/bat collisions
    if ball.y+ball.size > ponger.y-ponger.height:       
        # Get the distance from the center of the ponger
        dist=ball.x-ponger.x
    
        if abs(dist) > (ponger.width/2)+ball.size:
            quit=True
            if True==two_player:
                quit_other_player()
        elif abs(dist) > (ponger.width/2)-BAT_CORNER_SIZE:
            ball.velocity.reflect_v()
            
            # Get the distance from the corner (between 0 and corner_size)
            from_edge=abs(dist) - ((ponger.width/2)-BAT_CORNER_SIZE)
            if from_edge>BAT_CORNER_SIZE:
                from_edge=BAT_CORNER_SIZE
            
            # Get the change in angle that this corresponds to
            ang=BAT_CORNER_EFFECT * (from_edge / BAT_CORNER_SIZE)
            if dist<0:
                ang=-ang
            
            # Change the angle
            ball.velocity.set_ang(ang)
        else:
            ball.velocity.reflect_v()
           
        if ponger.push_force>0:
            ball.velocity.add_mag(1)

        # Force a xync with the server
        sync_counter=0


def render():
    # Clear the buffer
    img.clear((0,0,0))
    
    # Draw a rectangle at the ponger's position
    ponger.render(img)
    
    # Draw the other ponger
    if two_player:
        ponger2.render(img)
    
    # Draw the ball
    ball.render(img)
    
    # Make sure that we redraw the canvas
    handle_redraw()

def render_start_timer():
    w,h=canvas.size
    img.clear((0,0,0))
    img.text ( (w/2,h/2), u"%d"%(math.ceil(start_counter)), fill=(255,255,255), font='title' )
    ponger.render(img)
    if two_player:
        ponger2.render(img)
    handle_redraw()

def initialize_game():
    global quit
    global game_state
    global start_counter
    global ponger
    global ponger2
    global ball
    global canvas
    global img
    
    quit=False
    
    game_state=GAME_STATE_MENU
    start_counter=3
    
    # Go fullscreen for the game
    img=None
    appuifw.app.orientation='landscape'
    appuifw.app.screen='full'
    canvas=appuifw.Canvas ( redraw_callback=handle_redraw, event_callback=handle_event )
    appuifw.app.body=canvas

    # Create the off screen buffer
    w,h=canvas.size
    img=graphics.Image.new((w, h))
    img.clear((0,0,0))

    # Initialize the ponger
    ponger=Ponger()
    ponger.x=w/2
    ponger.y=h-5

    # Initialize the oponnents ponger
    if two_player:
        ponger2=Ponger()
        ponger2.x=w/2
        ponger2.y=5
   
    # Initialize the ball
    ball=Ball()
    ball.x=w/2
    ball.y=h/2
    
    # Initialize at a random angle
    ang=((random.random()*90)-45) * ( (math.pi*2)/360 )
    ball.velocity.from_av(ang, INITIAL_SPEED)
    
def initialize_menu():
    global img
    global canvas
    global game_state
    
    game_state=GAME_STATE_MENU
    # Create the canvas
    img=None
    appuifw.app.orientation='landscape'
    appuifw.app.screen='large'
    canvas=appuifw.Canvas ( redraw_callback=handle_redraw, event_callback=handle_event )
    appuifw.app.body=canvas
    
    # Create the off screen buffer
    w,h=canvas.size
    img=graphics.Image.new((w, h))
    img.clear((0,0,0))
    img.blit(backgroundImage, target=(100,0))
    menu_message(u"Select an option from the menu to continue")
    
    appuifw.app.menu = [(u"Practice game (single player)", start_single_player),
                        (u"Start game (2 player)", start_two_player),
                        (u"Join existing game", join_two_player),
                        (u"Quit", handle_quit)]

def play_game():
    global game_state
    global start_counter
    global sync_counter
       
    game_state=GAME_STATE_STARTING
    sync_counter=0

    # Enter the game loop
    while (False==quit):
        if GAME_STATE_STARTING==game_state:
            render_start_timer()
            start_counter-=TICK_TIME
            if start_counter<0:
                game_state=GAME_STATE_PLAYING
    
        elif GAME_STATE_PLAYING==game_state:
            # Sync if it's been a while
            if two_player:
                sync_counter-=1
                if sync_counter<=0:
                    if server:
                        send_state()
                    else:
                        parse_message()
                    sync_counter=2

            # Animate things
            animate()

            # Validate things
            validate()

            # Re-render everything
            render()

            # Stop the screensaver coming on (if we have the misty module present)
            if globals().__contains__('misty'):
                misty.reset_inactivity_time()

        # Sleep for a bit
        e32.ao_sleep(TICK_TIME)


def send_state():
    data=struct.pack('cxxxffffff', 'S', ball.x, ball.y, ball.velocity.x, ball.velocity.y, ponger.x, ponger.push_force)
    connection.send(data)
    parse_message()

def send_ponger():
    data=struct.pack('cxxxff', 'P', ponger.x, ponger.push_force)
    connection.send(data)

def quit_other_player():
    data=struct.pack('cxxx', 'D')
    connection.send(data)  

def parse_message():
    global quit
    w,h=canvas.size
    type="Unknown"

    # Get the message type
    try:
        string_data=connection.recv(struct.calcsize('cxxx'))
        data=struct.unpack('cxxx', string_data)
        type=data[0]
                   
        # 'D' means our opponent is dead
        if type=='D':
            quit=True
            
        elif type=='B':
            string_data=connection.recv(struct.calcsize('ffff'))
            data=struct.unpack('ffff', string_data)
            ball.x=data[0]
            ball.y=h-data[1]
            ball.velocity.x=data[2]
            ball.velocity.y=-data[3]

        # 'P' is just the ponger position
        elif type=='P':
            string_data=connection.recv(struct.calcsize('ff'))
            data=struct.unpack('ff', string_data)
            ponger2.x=data[0]
            ponger2.push_force=data[1]

        # 'S' is a the state of the server
        elif type=='S':
            string_data=connection.recv(struct.calcsize('ffffff'))
            data=struct.unpack('ffffff', string_data)
            ball.x=data[0]
            ball.y=h-data[1]
            ball.velocity.x=data[2]
            ball.velocity.y=-data[3]
            ponger2.x=data[4]
            ponger2.push_force=data[5]
            if False==server:
                send_ponger();

    except:
        pass
        #print "Failed reading message type : ", type, " ( server=",server,")"
        #print sys.exc_info()[0]

def start_single_player():
    global server
    global two_player
    two_player=False
    server=False
    initialize_game()
    play_game()
    initialize_menu()

def start_two_player():
    global two_player
    global server
    global connection

    menu_message(u"Creating connection")

    # OK, start the bluetooth server
    try:
        server_socket = socket.socket(socket.AF_BT, socket.SOCK_STREAM)
        server_socket.bind(("", BT_CHANNEL))
        menu_message(u"Waiting for opponent")
        server_socket.listen(1)
        socket.set_security(server_socket, socket.AUTH | socket.AUTHOR)
        socket.bt_advertise_service(BT_SERVICE_NAME, server_socket, True, socket.RFCOMM)
        connection, addr = server_socket.accept()
    except:
        menu_message(u"Failed to create connection")
        print sys.exc_info()[0]
        return

    # Get the first command - should be 'start'
    try:
        start=connection.recv(1024)
        if 'start'==start:
            two_player=True
            server=True
            initialize_game()
            play_game()
            initialize_menu()
        else:
            initialize_menu()
            menu_message(u"Recieved bad data")
    except:
        print sys.exc_info()[0]
        initialize_menu()
        menu_message(u"Connection failed")

    connection.close()
    server_socket.close()

def join_two_player():
    global two_player
    global server
    global connection
    
    # Print a message
    menu_message(u"Please wait, searching...")
    
    # Select the device from the list
    device=lightblue.selectdevice()
    menu_message(u"Conecting to %s"%device[1])

    # Connect to the channel
    try:
        connection = socket.socket(socket.AF_BT, socket.SOCK_STREAM)
        connection.connect((device[0], BT_CHANNEL))
    except:
        menu_message(u"Failed to connect to %s"%device[1])
        return

    try:
        # If we connected, send the starting flag
        connection.send("start")
        
        # Start the game in 2 player client mode
        two_player=True
        server=False
        initialize_game()
        play_game()
    except:
        pass

    initialize_menu()
    
    # Close the connection when we are done
    connection.close()

def menu_message(message):
    global canvas
    global img
    w,h=canvas.size
    img.clear((0,0,0))
    img.blit(backgroundImage, target=(100,0))
    img.text ( (10, h/2), unicode(message), fill=(255,255,255), font='dense')
    canvas.blit(img)

# Initialize and start the app
print "----------------------------------"
# Connect to the accelerometer
axyz.connect(read_xyz)
backgroundImage=graphics.Image.open('e:\\Python\\pong.png')
initialize_menu()

appuifw.app.exit_key_handler=handle_quit
appuifw.title=u"Pong"
app_lock=e32.Ao_lock()
app_lock.wait()
