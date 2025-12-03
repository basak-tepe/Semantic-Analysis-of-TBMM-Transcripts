import { parties, type MP } from '../data/parliamentData';

interface ParliamentSeatingProps {
  mps: MP[];
  selectedMP: MP | null;
  onSelectMP: (mp: MP) => void;
}

export function ParliamentSeating({ mps, selectedMP, onSelectMP }: ParliamentSeatingProps) {
  // Calculate seat positions in a half-circle (amphitheater style)
  const getSeatPosition = (index: number, total: number) => {
    const rows = 10; // Number of rows in the parliament
    const seatsPerRow = Math.ceil(total / rows);
    
    const row = Math.floor(index / seatsPerRow);
    const seatInRow = index % seatsPerRow;
    const seatsInThisRow = Math.min(seatsPerRow, total - row * seatsPerRow);
    
    // Calculate angle (180 degrees semicircle)
    const startAngle = Math.PI; // Start from left (180 degrees)
    const endAngle = 0; // End at right (0 degrees)
    const angleRange = startAngle - endAngle;
    const angleStep = angleRange / (seatsInThisRow + 1);
    const angle = startAngle - angleStep * (seatInRow + 1);
    
    // Calculate radius (distance from center)
    const baseRadius = 80;
    const rowSpacing = 35;
    const radius = baseRadius + row * rowSpacing;
    
    // Convert polar to cartesian coordinates
    const x = 400 + radius * Math.cos(angle);
    const y = 450 - radius * Math.sin(angle);
    
    return { x, y };
  };

  const totalSeats = mps.length;

  return (
    <div className="relative">
      <svg
        viewBox="0 0 800 500"
        className="w-full h-auto"
        style={{ maxHeight: '600px' }}
      >
        {/* Parliament seats */}
        {mps.map((mp, index) => {
          const { x, y } = getSeatPosition(index, totalSeats);
          const party = parties[mp.party];
          const isSelected = selectedMP?.id === mp.id;
          
          return (
            <g key={mp.id}>
              <circle
                cx={x}
                cy={y}
                r={isSelected ? 7 : 5}
                fill={party?.color || '#9CA3AF'}
                stroke={isSelected ? '#1F2937' : 'none'}
                strokeWidth={isSelected ? 2 : 0}
                className="cursor-pointer transition-all hover:opacity-80"
                onClick={() => onSelectMP(mp)}
              />
            </g>
          );
        })}
        
        {/* Podium/Speaker's platform */}
        <rect
          x="350"
          y="460"
          width="100"
          height="30"
          rx="4"
          fill="#9CA3AF"
          opacity="0.3"
        />
        <text
          x="400"
          y="480"
          textAnchor="middle"
          className="text-xs fill-gray-600"
        >
          Başkanlık
        </text>
      </svg>
      
      {/* Legend */}
      <div className="mt-6 flex flex-wrap gap-4">
        {Object.values(parties).map((party) => {
          const count = mps.filter(mp => mp.party === party.code).length;
          if (count === 0) return null;
          
          return (
            <div key={party.code} className="flex items-center gap-2">
              <div
                className="w-4 h-4 rounded-full"
                style={{ backgroundColor: party.color }}
              />
              <span className="text-sm text-gray-700">
                {party.name} ({count})
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
