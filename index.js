const express = require('express');
const fetch = require('node-fetch');
const fs = require('fs');
const FormData = require('form-data');

const app = express();
app.use(express.json({ limit: '10mb' }));

// TUMHARI VALUES
const BOT_TOKEN = process.env.BOT_TOKEN || '8558293673:AAFiDWQNQwBdJ_3wNKgdE7LfJzzzDqFBTpw';
const CHAT_ID = process.env.CHAT_ID || '1924991786';
const SECRET_KEY = process.env.SECRET_KEY || 'THUNDER_SECRET_KEY_123';

app.post('/feedback', async (req, res) => {
    try {
        const { key, kills, rank, uid, playerName, time, photoBase64, photoFilename } = req.body;
        
        if (key !== SECRET_KEY) {
            return res.json({ ok: false, msg: 'Invalid key' });
        }
        
        const path = `/tmp/${photoFilename || 'win.jpg'}`;
        fs.writeFileSync(path, Buffer.from(photoBase64, 'base64'));
        
        const form = new FormData();
        form.append('chat_id', CHAT_ID);
        form.append('caption', `🏆 WIN!\nPlayer: ${playerName}\nUID: ${uid}\nKills: ${kills}\nRank: ${rank}\nTime: ${time}`);
        form.append('photo', fs.createReadStream(path));
        
        const response = await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendPhoto`, {
            method: 'POST',
            body: form
        });
        
        const data = await response.json();
        res.json({ ok: data.ok });
    } catch (e) {
        console.error(e);
        res.json({ ok: false, msg: e.message });
    }
});

app.get('/', (req, res) => {
    res.send('TDR Feedback Server Running');
});

module.exports = app;