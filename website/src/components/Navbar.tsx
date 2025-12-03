import { Building2, Users, FileText, CalendarDays } from 'lucide-react';

interface NavbarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export function Navbar({ activeTab, onTabChange }: NavbarProps) {
  const navItems = [
    { id: 'parliament', label: 'Meclis', icon: Building2 },
    { id: 'committees', label: 'Semantic Shift', icon: Users },
    { id: 'legislation', label: 'Topic Analysis', icon: FileText },
    { id: 'sessions', label: 'Speech Statistics', icon: CalendarDays },
  ];

  return (
    <nav className="w-64 bg-white border-r border-gray-200 flex flex-col">
      <div className="p-6 border-b border-gray-200">
        <h1 className="text-red-600">Türkiye Büyük Millet Meclisi</h1>
      </div>
      
      <div className="flex-1 py-4">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`w-full px-6 py-3 flex items-center gap-3 transition-colors ${
                isActive
                  ? 'bg-red-50 text-red-600 border-r-2 border-red-600'
                  : 'text-gray-700 hover:bg-gray-50'
              }`}
            >
              <Icon className="w-5 h-5" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
