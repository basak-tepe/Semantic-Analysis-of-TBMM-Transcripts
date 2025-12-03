import { useState } from 'react';
import { terms } from '../data/parliamentData';
import { ParliamentSeating } from './ParliamentSeating';
import { MPInfoCard } from './MPInfoCard';
import type { MP } from '../data/parliamentData';

export function ParliamentView() {
  const [selectedTermIndex, setSelectedTermIndex] = useState(1); // Default to term 28 (index 1)
  const [selectedMP, setSelectedMP] = useState<MP | null>(null);

  const currentTerm = terms[selectedTermIndex];

  return (
    <div className="p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="mb-2">Türkiye Büyük Millet Meclisi</h1>
          <p className="text-gray-600">
            Meclis oturumunu görüntüleyin ve milletvekili bilgilerine erişin
          </p>
        </div>

        {/* Term Selector */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-8">
          <label htmlFor="term-slider" className="block mb-4">
            Dönem Seçimi: <span className="text-red-600">{currentTerm.id}</span> ({currentTerm.years})
          </label>
          <input
            id="term-slider"
            type="range"
            min="0"
            max={terms.length - 1}
            value={selectedTermIndex}
            onChange={(e) => {
              setSelectedTermIndex(Number(e.target.value));
              setSelectedMP(null); // Reset selected MP when changing term
            }}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-red-600"
          />
          <div className="flex justify-between mt-2 text-gray-600 text-sm">
            {terms.map((term, index) => (
              <span key={term.id} className={index === selectedTermIndex ? 'text-red-600' : ''}>
                {term.id}
              </span>
            ))}
          </div>
        </div>

        {/* Parliament Seating */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <ParliamentSeating
            mps={currentTerm.mps}
            selectedMP={selectedMP}
            onSelectMP={setSelectedMP}
          />
        </div>

        {/* MP Information */}
        {selectedMP && (
          <div className="mt-8">
            <MPInfoCard mp={selectedMP} />
          </div>
        )}
      </div>
    </div>
  );
}
