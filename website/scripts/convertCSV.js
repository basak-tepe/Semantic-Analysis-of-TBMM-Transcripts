const fs = require('fs');
const path = require('path');

// Read CSV file
const csvPath = path.join(__dirname, '../../mp_lookup.csv');
const csvContent = fs.readFileSync(csvPath, 'utf-8');

// Parse CSV
const lines = csvContent.trim().split('\n');
const data = [];

for (let i = 1; i < lines.length; i++) {
  const line = lines[i];
  if (!line.trim()) continue;

  // Handle quoted fields that may contain commas
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

  if (fields.length >= 3) {
    // Parse terms
    const termsStr = fields[2] || '[]';
    const cleaned = termsStr.replace(/[\[\]]/g, '').trim();
    const terms = cleaned ? cleaned.split(',').map(t => parseInt(t.trim(), 10)).filter(n => !isNaN(n)) : [];

    data.push({
      name: fields[0] || '',
      party: fields[1] || '',
      terms: terms,
    });
  }
}

// Write JSON file
const jsonPath = path.join(__dirname, '../src/data/mpData.json');
fs.writeFileSync(jsonPath, JSON.stringify(data, null, 2), 'utf-8');

console.log(`Converted ${data.length} MPs to JSON`);

