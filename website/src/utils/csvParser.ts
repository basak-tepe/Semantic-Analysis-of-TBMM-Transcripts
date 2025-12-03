// Simple CSV parser for mp_lookup.csv
export function parseCSV(csvText: string): Array<{ speech_giver: string; political_party: string; terms: string }> {
  const lines = csvText.trim().split('\n');
  const headers = lines[0].split(',');
  const data: Array<{ speech_giver: string; political_party: string; terms: string }> = [];

  for (let i = 1; i < lines.length; i++) {
    const line = lines[i];
    if (!line.trim()) continue;

    // Handle quoted fields that may contain commas
    const fields: string[] = [];
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
      data.push({
        speech_giver: fields[0] || '',
        political_party: fields[1] || '',
        terms: fields[2] || '[]',
      });
    }
  }

  return data;
}

// Parse terms array string like "[27, 28]" or "[]"
export function parseTerms(termsStr: string): number[] {
  try {
    // Remove brackets and parse
    const cleaned = termsStr.replace(/[\[\]]/g, '').trim();
    if (!cleaned) return [];
    
    return cleaned.split(',').map(t => parseInt(t.trim(), 10)).filter(n => !isNaN(n));
  } catch {
    return [];
  }
}

// Map party names to party codes
export function normalizePartyName(partyStr: string): string {
  if (!partyStr) return 'IND';
  
  const upperParty = partyStr.toUpperCase();
  
  // Check for common party name patterns
  if (upperParty.includes('ADALET VE KALKINMA') || upperParty.includes('AK PARTİ') || upperParty.includes('AKP')) {
    return 'AKP';
  }
  if (upperParty.includes('CUMHURİYET HALK') || upperParty.includes('CHP')) {
    return 'CHP';
  }
  if (upperParty.includes('MİLLİYETÇİ HAREKET') || upperParty.includes('MHP')) {
    return 'MHP';
  }
  if (upperParty.includes('İYİ PARTİ') || upperParty.includes('İYİ PARTİ')) {
    return 'IYI';
  }
  if (upperParty.includes('HALKların DEMOKRATİK') || upperParty.includes('HDP') || upperParty.includes('DEM PARTİ')) {
    return 'HDP';
  }
  if (upperParty.includes('DEMOKRASİ VE ATILIM') || upperParty.includes('DEVA')) {
    return 'DEVA';
  }
  if (upperParty.includes('SAADET') || upperParty.includes('SP')) {
    return 'SP';
  }
  if (upperParty.includes('BAĞIMSIZ') || upperParty.includes('INDEPENDENT')) {
    return 'IND';
  }
  
  return 'IND'; // Default to independent
}

