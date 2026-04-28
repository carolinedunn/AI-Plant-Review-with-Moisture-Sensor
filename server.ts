import express from 'express';
import { createServer as createViteServer } from 'vite';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';
import admin from 'firebase-admin';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load Firebase Config for Admin SDK
const firebaseConfigPath = path.join(process.cwd(), 'firebase-applet-config.json');
let firebaseConfig: any = {};
if (fs.existsSync(firebaseConfigPath)) {
  firebaseConfig = JSON.parse(fs.readFileSync(firebaseConfigPath, 'utf-8'));
}

// Initialize Firebase Admin
if (firebaseConfig.projectId) {
  admin.initializeApp({
    projectId: firebaseConfig.projectId,
  });
} else {
  // Fallback for environment where config might be in env vars
  admin.initializeApp();
}

const db = admin.firestore(firebaseConfig.firestoreDatabaseId);
const snapshotsCol = db.collection('snapshots');

interface Snapshot {
  image: string;
  timestamp: number;
  moisture: number | null;
  score: number | null;
  analysis: string | null;
}

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json({ limit: '10mb' }));

  // Debug logging
  app.use((req, res, next) => {
    if (req.url.startsWith('/api')) {
      console.log(`[${req.method}] ${req.url}`);
    }
    next();
  });

  // API Route for receiving images from Raspberry Pi
  app.post('/api/upload-image', async (req, res) => {
    const { image, secret, score, analysis, moisture } = req.body;
    
    // Check secret
    const expectedSecret = process.env.UPLOAD_SECRET || "Caroline";
    if (secret !== expectedSecret) {
      console.log(`[POST] /api/upload-image: Unauthorized access attempt`);
      return res.status(401).json({ error: 'Unauthorized' });
    }

    if (!image) return res.status(400).json({ error: 'No image data provided' });
    
    const timestamp = Date.now();
    
    try {
      await snapshotsCol.add({
        image,
        timestamp,
        moisture: moisture !== undefined ? Number(moisture) : null,
        score: score || null,
        analysis: analysis || null
      });
      
      console.log(`[POST] /api/upload-image: Saved to Firestore (Moisture: ${moisture}%)`);
      res.json({ status: 'ok', timestamp });
    } catch (err) {
      console.error('Error saving to Firestore:', err);
      res.status(500).json({ error: 'Failed to save snapshot' });
    }
  });

  // API Route to fetch latest image 
  app.get('/api/latest-image', async (req, res) => {
    try {
      const snapshot = await snapshotsCol.orderBy('timestamp', 'desc').limit(1).get();
      if (snapshot.empty) return res.status(404).json({ error: 'No snapshots found' });
      
      const data = snapshot.docs[0].data();
      res.json(data);
    } catch (err) {
      console.error('Error fetching latest from Firestore:', err);
      res.status(500).json({ error: 'Failed to fetch snapshot' });
    }
  });

  // Vite middleware for development
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(__dirname, 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running at http://0.0.0.0:${PORT}`);
  });
}

startServer();
