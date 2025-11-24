const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');
const FormData = require('form-data');
const express = require('express');

const API_URL = process.env.API_URL || 'http://localhost:5000/api/recognize';

// Express App
const app = express();
app.use(express.json());

// WhatsApp client
const client = new Client({
  authStrategy: new LocalAuth(),
  puppeteer: { 
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  },
});

// QR Auth
client.on('qr', qr => {
  console.log('📱 Scan this QR code with WhatsApp:');
  qrcode.generate(qr, { small: true });
});

client.on('authenticated', () => console.log('✅ Client Authenticated!'));
client.on('ready', () => {
  console.log('✅ WhatsApp Bot is Ready!');
  console.log(`🔗 Connected to API: ${API_URL}`);
  console.log('📨 Waiting for messages...\n');
});
client.on('disconnected', reason => console.log(`❌ Disconnected: ${reason}`));

// Handle image messages
client.on('message', async (message) => {
  try {
    // Extract phone number (strip @c.us and other formatting)
    const sender = message.from.replace(/\D/g, '');
    const isGroup = message.from.endsWith('@g.us');
    
    console.log(`📩 Message from: ${sender}, Type: ${message.type}, Group: ${isGroup}`);

    // ✅ Process all image messages (no restriction)
    if (message.hasMedia && message.type === 'image') {
      console.log(`📸 Processing image from ${sender}...`);
      
      // Send "processing" message to user
      await message.reply('🔍 Processing your image, please wait...');

      const mediaData = await message.downloadMedia();
      
      // Convert base64 → buffer
      const buffer = Buffer.from(mediaData.data, 'base64');

      // ---------- Send image to Face Recognition API ----------
      const formData = new FormData();
      formData.append('image', buffer, {
        filename: `IMG_${Date.now()}.jpg`,
        contentType: mediaData.mimetype,
      });
      formData.append('mobile_number', sender);

      console.log(`🚀 Sending image to API: ${API_URL}`);
      
      const res = await axios.post(API_URL, formData, {
        headers: formData.getHeaders(),
        timeout: 60000, // 60 second timeout
      });
      
      const apiResponse = res.data;
      console.log('✅ API Response:', JSON.stringify(apiResponse, null, 2));

      // ---------- Reply to User ----------
      let replyMessage = '';
      
      if (apiResponse.success) {
        // Face detected and processed successfully
        if (apiResponse.recognized) {
          // Face recognized (recognized field is true)
          replyMessage = `✅ *Face Recognized!*\n\n`;
          replyMessage += `👤 *Name:* ${apiResponse.person_name}\n`;
          replyMessage += `🎯 *Confidence:* ${(apiResponse.confidence * 100).toFixed(2)}%\n`;
          replyMessage += `⏱️ *Processing Time:* ${apiResponse.processing_time.toFixed(2)}s\n`;
          
          // Add description if available
          if (apiResponse.description) {
            replyMessage += `\n� *Description:*\n${apiResponse.description}\n`;
          }
        } else {
          // Face detected but not recognized (recognized field is false)
          replyMessage = `❌ *Face Not Recognized*\n\n`;
          replyMessage += `The person in the image is not in our database.\n`;
          replyMessage += `⏱️ *Processing Time:* ${apiResponse.processing_time.toFixed(2)}s`;
        }
      } else {
        // API error or no face detected (success is false)
        replyMessage = `⚠️ *Error:* ${apiResponse.error || 'Unable to process the image. Please try again.'}`;
        if (apiResponse.processing_time) {
          replyMessage += `\n⏱️ *Processing Time:* ${apiResponse.processing_time.toFixed(2)}s`;
        }
      }

      await message.reply(replyMessage);

      console.log('✅ Response sent to user\n');
      
    } else if (message.body && message.body.toLowerCase().includes('help')) {
      // Help command
      await message.reply(
        '🤖 *Face Recognition Bot*\n\n' +
        'Send me an image and I will recognize the face!\n\n' +
        '📸 Just send any image and I\'ll process it automatically.\n' +
        '⏱️ Processing usually takes 5-10 seconds.\n\n' +
        'Powered by ArcFace Face Recognition System'
      );
    }
    
  } catch (err) {
    console.error('❌ Error processing message:', err.response?.data || err.message);
    
    // Send error message to user
    await message.reply(
      '⚠️ *Error Processing Image*\n\n' +
      'Sorry, there was an error processing your image.\n' +
      'Please try again or contact support.\n\n' +
      `Error: ${err.message}`
    );
  }
});

// API Endpoint to send alert
app.post('/send-alert', async (req, res) => {
    const { message, to } = req.body;
    if (!message || !to) {
        return res.status(400).json({ success: false, error: 'Message and recipient number are required.' });
    }

    try {
        // Sanitize the number by removing non-digit characters
        const sanitizedTo = to.replace(/\D/g, '');
        const chatId = `${sanitizedTo}@c.us`;

        await client.sendMessage(chatId, message);
        console.log(`✅ Alert sent to ${to}`);
        res.json({ success: true, message: 'Alert sent successfully.' });
    } catch (error) {
        console.error('❌ Error sending alert:', error.message);
        res.status(500).json({ success: false, error: 'Failed to send alert.' });
    }
});


// Graceful shutdown
process.on('SIGINT', async () => {
  console.log('\n🛑 Shutting down WhatsApp bot...');
  await client.destroy();
  process.exit(0);
});

// Start WhatsApp client
console.log('🚀 Starting WhatsApp Bot...');
console.log(`🔗 API URL: ${API_URL}\n`);
client.initialize();

// Start Express server
const PORT = process.env.PORT || 8080;
app.listen(PORT, () => {
    console.log(`🚀 Alert server listening on port ${PORT}`);
});
