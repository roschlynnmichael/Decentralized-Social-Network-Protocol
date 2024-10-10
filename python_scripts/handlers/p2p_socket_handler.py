from flask_socketio import SocketIO, emit, join_room, leave_room

class P2PSocketHandler:
    def __init__(self, app):
        self.socketio = SocketIO(app, cors_allowed_origins="*")
        self.setup_socket_events()

    def setup_socket_events(self):
        @self.socketio.on('connect')
        def handle_connect():
            print("Client connected")
            pass
        @self.socketio.on('disconnect')
        def handle_disconnect():
            print("Client disconnected")
            pass
        @self.socketio.on('send_message')
        def handle_send_message(data):
            pass
        @self.socketio.on('join_room')
        def handle_join_room(data):
            pass

    def run(self, app, debug = True):
        self.socketio.run(app, debug=debug)
            
