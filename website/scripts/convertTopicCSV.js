const fs = require('fs');
const path = require('path');

// Read CSV file
const csvPath = path.join(__dirname, '../../data/topic_summary.csv');
const csvContent = fs.readFileSync(csvPath, 'utf-8');

// Parse CSV
const lines = csvContent.trim().split('\n');
const headers = lines[0].split(',');

const data = [];

for (let i = 1; i < lines.length; i++) {
  const line = lines[i];
  if (!line.trim()) continue;

  // Handle CSV parsing with quoted fields
  const fields = [];
  let currentField = '';
  let inQuotes = false;

  for (let j = 0; j < line.length; j++) {
    const char = line[j];
    if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === ',' && !inQuotes) {
      fields.push(currentField.trim());
      currentField = '';
    } else {
      currentField += char;
    }
  }
  fields.push(currentField.trim());

  if (fields.length >= 4) {
    const topic = parseInt(fields[1], 10);
    const count = parseInt(fields[2], 10);
    const totalCount = parseInt(fields[3], 10);
    
    if (!isNaN(topic) && !isNaN(count) && !isNaN(totalCount)) {
      data.push({
        speech_giver: fields[0] || '',
        topic: topic,
        count: count,
        totalCount: totalCount,
        topicName: fields[4] || `Topic ${topic}`,
        representation: fields[5] || '',
        representativeDocs: fields[6] || '',
      });
    }
  }
}

// Write JSON file
const jsonPath = path.join(__dirname, '../src/data/topicData.json');
fs.writeFileSync(jsonPath, JSON.stringify(data, null, 2), 'utf-8');

console.log(`Converted ${data.length} topic-MP relationships to JSON`);
console.log(`Unique MPs: ${new Set(data.map(d => d.speech_giver)).size}`);
console.log(`Unique Topics: ${new Set(data.map(d => d.topic)).size}`);

