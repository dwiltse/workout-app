// Simple script to create placeholder icons for PWA
const fs = require('fs');

// Create SVG icons as placeholder
const createIcon = (size) => {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${size} ${size}" width="${size}" height="${size}">
    <rect width="${size}" height="${size}" rx="${size/6}" fill="#007AFF"/>
    <text x="${size/2}" y="${size*0.7}" font-family="Arial" font-size="${size*0.4}" fill="white" text-anchor="middle">💪</text>
  </svg>`;
};

// Create placeholder icons
const icon192 = createIcon(192);
const icon512 = createIcon(512);

// Write to files
fs.writeFileSync('public/icon-192.svg', icon192);
fs.writeFileSync('public/icon-512.svg', icon512);
fs.writeFileSync('public/icon-192-maskable.svg', icon192); // Same for now

console.log('✅ Created placeholder icons (SVG format)');
console.log('💡 Replace with PNG icons later for better browser support');