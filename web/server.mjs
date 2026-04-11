import { createServer } from 'http';
import { parse } from 'url';
import next from 'next';
import { Server as SocketIOServer } from 'socket.io';

const dev = process.env.NODE_ENV !== 'production';
const app = next({ dev });
const handle = app.getRequestHandler();

app.prepare().then(() => {
  const server = createServer((req, res) => {
    const parsedUrl = parse(req.url, true);
    handle(req, res, parsedUrl);
  });

  const io = new SocketIOServer(server, {
    cors: { origin: '*' },
    path: '/api/socketio'
  });

  const onlineUsers = new Map();

  io.on('connection', (socket) => {
    console.log('Socket connected:', socket.id);

    socket.on('authenticate', (userId) => {
      socket.data.userId = userId;
      onlineUsers.set(userId, socket.id);
      socket.emit('online-users', Array.from(onlineUsers.keys()));
      io.emit('user-online', { userId });
    });

    socket.on('join-chat', (chatId) => {
      socket.join(chatId);
    });

    socket.on('leave-chat', (chatId) => {
      socket.leave(chatId);
    });

    socket.on('send-message', (data) => {
      io.to(data.chatId).emit('new-message', data.message);
    });

    socket.on('typing', (data) => {
      socket.to(data.chatId).emit('user-typing', data);
    });

    // WebRTC signaling
    socket.on('call-offer', (data) => {
      io.to(data.targetSocketId).emit('call-offer', data);
    });

    socket.on('call-answer', (data) => {
      io.to(data.targetSocketId).emit('call-answer', data);
    });

    socket.on('call-ice-candidate', (data) => {
      io.to(data.targetSocketId).emit('call-ice-candidate', data);
    });

    socket.on('call-hangup', (data) => {
      io.to(data.chatId).emit('call-hangup', data);
    });

    socket.on('disconnect', () => {
      const userId = socket.data.userId;
      if (userId) {
        onlineUsers.delete(userId);
        io.emit('user-offline', { userId });
      }
      console.log('Socket disconnected:', socket.id);
    });
  });

  server.listen(3000, () => {
    console.log('> Ready on http://localhost:3000');
  });
});
