import { User, Flag, Calendar } from 'lucide-react';
import { parties, type MP } from '../data/parliamentData';

interface MPInfoCardProps {
  mp: MP;
}

export function MPInfoCard({ mp }: MPInfoCardProps) {
  const party = parties[mp.party];

  return (
    <div className="bg-white rounded-lg shadow-md p-6 border-l-4" style={{ borderLeftColor: party?.color || '#9CA3AF' }}>
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div
            className="w-12 h-12 rounded-full flex items-center justify-center"
            style={{ backgroundColor: `${party?.color}20` }}
          >
            <User className="w-6 h-6" style={{ color: party?.color }} />
          </div>
          <div>
            <h2 className="text-gray-900">{mp.name}</h2>
            <p className="text-sm text-gray-500">Milletvekili</p>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex items-center gap-3 text-gray-700">
          <Flag className="w-5 h-5 text-gray-400" />
          <div>
            <p className="text-sm text-gray-500">Parti</p>
            <p>{party?.name || mp.party}</p>
          </div>
        </div>

        <div className="flex items-center gap-3 text-gray-700">
          <Calendar className="w-5 h-5 text-gray-400" />
          <div>
            <p className="text-sm text-gray-500">Görev Yılları</p>
            <p>{mp.servedYears}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
