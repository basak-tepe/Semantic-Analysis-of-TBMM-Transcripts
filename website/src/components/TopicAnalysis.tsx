import { useState, useMemo, useEffect } from 'react';
import { BarChart3, TrendingUp, TrendingDown, Users, UserX, Activity, UserCheck, Search } from 'lucide-react';

interface TopicData {
  speech_giver: string;
  topic: number;
  count: number;
  totalCount: number;
  topicName: string;
  representation: string;
  representativeDocs: string;
}

export function TopicAnalysis() {
  const [selectedMP, setSelectedMP] = useState<string>('');
  const [selectedTopic, setSelectedTopic] = useState<number | null>(null);
  const [topicData, setTopicData] = useState<TopicData[]>([]);
  const [loading, setLoading] = useState(true);

  // Load data dynamically
  useEffect(() => {
    // Use import() for better Vite handling of large JSON files
    import('../data/topicData.json')
      .then(module => {
        setTopicData(module.default);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load topic data:', err);
        setLoading(false);
      });
  }, []);

  // Process data for analysis
  const analysis = useMemo(() => {
    if (topicData.length === 0) return {
      dominantTopics: [],
      overlookedTopics: [],
      mpTopicMap: new Map(),
      mpTotalSpeeches: new Map(),
      mostActive: [],
      mostPassive: [],
      mpTopicEngagement: new Map(),
    };
    // Q2: Which subjects persisted and were dominant?
    const topicTotals = new Map<number, { count: number; name: string }>();
    topicData.forEach((d: TopicData) => {
      const current = topicTotals.get(d.topic) || { count: 0, name: d.topicName };
      topicTotals.set(d.topic, {
        count: current.count + d.count,
        name: d.topicName,
      });
    });
    const dominantTopics = Array.from(topicTotals.entries())
      .map(([topic, data]) => ({ topic, ...data }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);

    // Q3: Which subjects did not come up often and were overlooked?
    const overlookedTopics = Array.from(topicTotals.entries())
      .map(([topic, data]) => ({ topic, ...data }))
      .sort((a, b) => a.count - b.count)
      .slice(0, 10);

    // Q6 & Q7: Which MPs talked about which subject / did not talk about which subject
    const mpTopicMap = new Map<string, Set<number>>();
    const mpTotalSpeeches = new Map<string, number>();
    
    topicData.forEach((d: TopicData) => {
      if (!mpTopicMap.has(d.speech_giver)) {
        mpTopicMap.set(d.speech_giver, new Set());
      }
      mpTopicMap.get(d.speech_giver)!.add(d.topic);
      mpTotalSpeeches.set(d.speech_giver, d.totalCount);
    });

    // Q8 & Q9: Most active and passive MPs
    const mpActivity = Array.from(mpTotalSpeeches.entries())
      .map(([mp, total]) => ({
        mp,
        total,
        topics: mpTopicMap.get(mp)?.size || 0,
      }))
      .sort((a, b) => b.total - a.total);

    const mostActive = mpActivity.slice(0, 10);
    const mostPassive = mpActivity.slice(-10).reverse();

    // Q10 & Q11: MP-topic dominance and avoidance
    const mpTopicEngagement = new Map<string, Map<number, { count: number; ratio: number }>>();
    
    topicData.forEach((d: TopicData) => {
      if (!mpTopicEngagement.has(d.speech_giver)) {
        mpTopicEngagement.set(d.speech_giver, new Map());
      }
      const mpTopics = mpTopicEngagement.get(d.speech_giver)!;
      const ratio = d.totalCount > 0 ? d.count / d.totalCount : 0;
      mpTopics.set(d.topic, { count: d.count, ratio });
    });

    return {
      dominantTopics,
      overlookedTopics,
      mpTopicMap,
      mpTotalSpeeches,
      mostActive,
      mostPassive,
      mpTopicEngagement,
    };
  }, [topicData]);

  // Get MP-specific data
  const mpData = useMemo(() => {
    if (!selectedMP) return null;

    const mpTopics = analysis.mpTopicMap.get(selectedMP);
    const allTopics = new Set(topicData.map((d: TopicData) => d.topic));
    const topicsNotTalked = Array.from(allTopics).filter(t => !mpTopics?.has(t));
    
    const engagement = analysis.mpTopicEngagement.get(selectedMP);
    const dominantTopics = Array.from(engagement?.entries() || [])
      .map(([topic, data]) => ({
        topic,
        ...data,
        topicName: topicData.find((d: TopicData) => d.topic === topic)?.topicName || `Topic ${topic}`,
      }))
      .sort((a, b) => b.ratio - a.ratio)
      .slice(0, 5);

    const avoidedTopics = topicsNotTalked
      .map(topic => ({
        topic,
        topicName: topicData.find((d: TopicData) => d.topic === topic)?.topicName || `Topic ${topic}`,
      }))
      .slice(0, 5);

    return {
      dominantTopics,
      avoidedTopics,
      totalSpeeches: analysis.mpTotalSpeeches.get(selectedMP) || 0,
      topicsCovered: mpTopics?.size || 0,
    };
  }, [selectedMP, analysis]);

  // Get topic-specific data
  const topicDataForTopic = useMemo(() => {
    if (selectedTopic === null) return null;

    const mpEngagements = topicData
      .filter((d: TopicData) => d.topic === selectedTopic)
      .map((d: TopicData) => ({
        mp: d.speech_giver,
        count: d.count,
        ratio: d.totalCount > 0 ? d.count / d.totalCount : 0,
        totalSpeeches: d.totalCount,
      }))
      .sort((a, b) => b.count - a.count);

    const mpNotTalked = Array.from(analysis.mpTopicMap.entries())
      .filter(([mp, topics]) => !topics.has(selectedTopic))
      .map(([mp]) => mp)
      .slice(0, 10);

    return {
      mpEngagements: mpEngagements.slice(0, 10),
      mpNotTalked,
      topicName: topicData.find((d: TopicData) => d.topic === selectedTopic)?.topicName || `Topic ${selectedTopic}`,
    };
  }, [selectedTopic, analysis]);

  const allMPs = Array.from(analysis.mpTopicMap.keys()).sort();
  const allTopics = Array.from(new Set(topicData.map((d: TopicData) => d.topic))).sort((a, b) => a - b);

  if (loading) {
    return (
      <div className="p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Loading topic data...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold mb-2">Topic Analysis</h1>
        <p className="text-gray-600 mb-8">
          Analyzing parliamentary discourse patterns and MP-topic relationships
        </p>

        {/* Q2: Dominant Topics */}
        <section className="bg-white rounded-lg shadow-sm p-6 mb-8">
          <div className="flex items-center gap-3 mb-4">
            <TrendingUp className="w-6 h-6 text-green-600" />
            <h2 className="text-xl font-semibold">Q2: Which subjects persisted and were dominant?</h2>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {analysis.dominantTopics.map(({ topic, count, name }) => (
              <div key={topic} className="border rounded-lg p-4 hover:bg-gray-50 cursor-pointer"
                   onClick={() => setSelectedTopic(topic)}>
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-medium text-gray-900">{name}</p>
                    <p className="text-sm text-gray-500">Topic {topic}</p>
                  </div>
                  <span className="text-lg font-bold text-green-600">{count.toLocaleString()}</span>
                </div>
                <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-green-600 h-2 rounded-full"
                    style={{ width: `${(count / analysis.dominantTopics[0].count) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Q3: Overlooked Topics */}
        <section className="bg-white rounded-lg shadow-sm p-6 mb-8">
          <div className="flex items-center gap-3 mb-4">
            <TrendingDown className="w-6 h-6 text-red-600" />
            <h2 className="text-xl font-semibold">Q3: Which subjects did not come up often and were overlooked?</h2>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {analysis.overlookedTopics.map(({ topic, count, name }) => (
              <div key={topic} className="border rounded-lg p-4 hover:bg-gray-50 cursor-pointer"
                   onClick={() => setSelectedTopic(topic)}>
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-medium text-gray-900">{name}</p>
                    <p className="text-sm text-gray-500">Topic {topic}</p>
                  </div>
                  <span className="text-lg font-bold text-red-600">{count.toLocaleString()}</span>
                </div>
                <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-red-600 h-2 rounded-full"
                    style={{ width: `${Math.max((count / analysis.dominantTopics[0].count) * 100, 1)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Q8: Most Active MPs */}
        <section className="bg-white rounded-lg shadow-sm p-6 mb-8">
          <div className="flex items-center gap-3 mb-4">
            <Activity className="w-6 h-6 text-blue-600" />
            <h2 className="text-xl font-semibold">Q8: Which MPs contributed to the discourse the most and were the most active?</h2>
          </div>
          <div className="space-y-3">
            {analysis.mostActive.map(({ mp, total, topics }, idx) => (
              <div key={mp} className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50 cursor-pointer"
                   onClick={() => setSelectedMP(mp)}>
                <div className="flex items-center gap-4">
                  <span className="text-gray-500 font-medium w-8">#{idx + 1}</span>
                  <div>
                    <p className="font-medium text-gray-900">{mp}</p>
                    <p className="text-sm text-gray-500">{topics} different topics</p>
                  </div>
                </div>
                <span className="text-lg font-bold text-blue-600">{total.toLocaleString()} speeches</span>
              </div>
            ))}
          </div>
        </section>

        {/* Q9: Most Passive MPs */}
        <section className="bg-white rounded-lg shadow-sm p-6 mb-8">
          <div className="flex items-center gap-3 mb-4">
            <UserX className="w-6 h-6 text-gray-600" />
            <h2 className="text-xl font-semibold">Q9: Which MPs did not contribute to the discourse often and were on the passive side?</h2>
          </div>
          <div className="space-y-3">
            {analysis.mostPassive.map(({ mp, total, topics }, idx) => (
              <div key={mp} className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50 cursor-pointer"
                   onClick={() => setSelectedMP(mp)}>
                <div className="flex items-center gap-4">
                  <span className="text-gray-500 font-medium w-8">#{idx + 1}</span>
                  <div>
                    <p className="font-medium text-gray-900">{mp}</p>
                    <p className="text-sm text-gray-500">{topics} different topics</p>
                  </div>
                </div>
                <span className="text-lg font-bold text-gray-600">{total.toLocaleString()} speeches</span>
              </div>
            ))}
          </div>
        </section>

        {/* MP Selector */}
        <section className="bg-white rounded-lg shadow-sm p-6 mb-8">
          <div className="flex items-center gap-3 mb-4">
            <Search className="w-6 h-6 text-purple-600" />
            <h2 className="text-xl font-semibold">Select MP for Detailed Analysis</h2>
          </div>
          <select
            value={selectedMP}
            onChange={(e) => setSelectedMP(e.target.value)}
            className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
          >
            <option value="">Select an MP...</option>
            {allMPs.map(mp => (
              <option key={mp} value={mp}>{mp}</option>
            ))}
          </select>
        </section>

        {/* Q10 & Q11: MP-specific analysis */}
        {mpData && (
          <>
            <section className="bg-white rounded-lg shadow-sm p-6 mb-8">
              <div className="flex items-center gap-3 mb-4">
                <UserCheck className="w-6 h-6 text-green-600" />
                <h2 className="text-xl font-semibold">
                  Q10: Which MP talked about which subject dominantly? ({selectedMP})
                </h2>
              </div>
              <div className="mb-4 p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600">
                  Total Speeches: <span className="font-semibold">{mpData.totalSpeeches}</span> | 
                  Topics Covered: <span className="font-semibold">{mpData.topicsCovered}</span>
                </p>
              </div>
              <div className="space-y-3">
                {mpData.dominantTopics.map(({ topic, ratio, count, topicName }) => (
                  <div key={topic} className="border rounded-lg p-4">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <p className="font-medium text-gray-900">{topicName}</p>
                        <p className="text-sm text-gray-500">Topic {topic}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-lg font-bold text-green-600">{(ratio * 100).toFixed(1)}%</p>
                        <p className="text-sm text-gray-500">{count} speeches</p>
                      </div>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-green-600 h-2 rounded-full"
                        style={{ width: `${ratio * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className="bg-white rounded-lg shadow-sm p-6 mb-8">
              <div className="flex items-center gap-3 mb-4">
                <UserX className="w-6 h-6 text-red-600" />
                <h2 className="text-xl font-semibold">
                  Q11: Which MP avoided or did not contribute to which subjects? ({selectedMP})
                </h2>
              </div>
              <div className="grid grid-cols-2 gap-4">
                {mpData.avoidedTopics.map(({ topic, topicName }) => (
                  <div key={topic} className="border rounded-lg p-4 hover:bg-gray-50 cursor-pointer"
                       onClick={() => setSelectedTopic(topic)}>
                    <p className="font-medium text-gray-900">{topicName}</p>
                    <p className="text-sm text-gray-500">Topic {topic}</p>
                  </div>
                ))}
              </div>
            </section>
          </>
        )}

        {/* Topic Selector */}
        <section className="bg-white rounded-lg shadow-sm p-6 mb-8">
          <div className="flex items-center gap-3 mb-4">
            <BarChart3 className="w-6 h-6 text-indigo-600" />
            <h2 className="text-xl font-semibold">Select Topic for Detailed Analysis</h2>
          </div>
          <select
            value={selectedTopic ?? ''}
            onChange={(e) => setSelectedTopic(e.target.value ? parseInt(e.target.value) : null)}
            className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          >
            <option value="">Select a topic...</option>
            {allTopics.map(topic => {
              const topicName = topicData.find((d: TopicData) => d.topic === topic)?.topicName || `Topic ${topic}`;
              return (
                <option key={topic} value={topic}>{topicName} (Topic {topic})</option>
              );
            })}
          </select>
        </section>

        {/* Q6 & Q7: Topic-specific analysis */}
        {topicDataForTopic && (
          <>
            <section className="bg-white rounded-lg shadow-sm p-6 mb-8">
              <div className="flex items-center gap-3 mb-4">
                <Users className="w-6 h-6 text-blue-600" />
                <h2 className="text-xl font-semibold">
                  Q6: Which MPs talked about which subject? ({topicDataForTopic.topicName})
                </h2>
              </div>
              <div className="space-y-3">
                {topicDataForTopic.mpEngagements.map(({ mp, count, ratio, totalSpeeches }) => (
                  <div key={mp} className="border rounded-lg p-4 hover:bg-gray-50 cursor-pointer"
                       onClick={() => setSelectedMP(mp)}>
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="font-medium text-gray-900">{mp}</p>
                        <p className="text-sm text-gray-500">
                          {count} speeches ({((count / totalSpeeches) * 100).toFixed(1)}% of their total)
                        </p>
                      </div>
                      <span className="text-lg font-bold text-blue-600">{count}</span>
                    </div>
                    <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full"
                        style={{ width: `${ratio * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className="bg-white rounded-lg shadow-sm p-6 mb-8">
              <div className="flex items-center gap-3 mb-4">
                <UserX className="w-6 h-6 text-gray-600" />
                <h2 className="text-xl font-semibold">
                  Q7: Which MPs did not talk about which subject? ({topicDataForTopic.topicName})
                </h2>
              </div>
              <div className="grid grid-cols-3 gap-3">
                {topicDataForTopic.mpNotTalked.map(mp => (
                  <div key={mp} className="border rounded-lg p-3 hover:bg-gray-50 cursor-pointer text-sm"
                       onClick={() => setSelectedMP(mp)}>
                    <p className="font-medium text-gray-900">{mp}</p>
                  </div>
                ))}
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  );
}

