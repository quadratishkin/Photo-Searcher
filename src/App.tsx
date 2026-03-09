import { useEffect, useState } from 'react';

type TabId = 'library' | 'search' | 'people';

type PhotoItem = {
  id: number;
  src: string;
};

const tabs: Array<{ id: TabId; label: string }> = [
  { id: 'library', label: 'Медиа' },
  { id: 'search', label: 'Поиск' },
  { id: 'people', label: 'Люди' },
];

const photos: PhotoItem[] = [
  { id: 1, src: 'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?auto=format&fit=crop&w=900&q=80' },
  { id: 2, src: 'https://images.unsplash.com/photo-1511499767150-a48a237f0083?auto=format&fit=crop&w=900&q=80' },
  { id: 3, src: 'https://images.unsplash.com/photo-1492691527719-9d1e07e534b4?auto=format&fit=crop&w=900&q=80' },
  { id: 4, src: 'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=900&q=80' },
  { id: 5, src: 'https://images.unsplash.com/photo-1527631746610-bca00a040d60?auto=format&fit=crop&w=900&q=80' },
  { id: 6, src: 'https://images.unsplash.com/photo-1511988617509-a57c8a288659?auto=format&fit=crop&w=900&q=80' },
  { id: 7, src: 'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?auto=format&fit=crop&w=900&q=80' },
  { id: 8, src: 'https://images.unsplash.com/photo-1504198453319-5ce911bafcde?auto=format&fit=crop&w=900&q=80' },
  { id: 9, src: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=900&q=80' },
  { id: 10, src: 'https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?auto=format&fit=crop&w=900&q=80' },
  { id: 11, src: 'https://images.unsplash.com/photo-1470770903676-69b98201ea1c?auto=format&fit=crop&w=900&q=80' },
  { id: 12, src: 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=900&q=80' },
];

const people = [
  { id: 1, name: 'Anna', count: 28, hint: 'Beach portraits and city walks' },
  { id: 2, name: 'Maksim', count: 14, hint: 'Studio and outdoor shots' },
  { id: 3, name: 'Unsorted', count: 9, hint: 'Needs name assignment' },
];

function App() {
  const [activeTab, setActiveTab] = useState<TabId>('library');
  const [animateView, setAnimateView] = useState(false);

  useEffect(() => {
    setAnimateView(false);
    const frame = requestAnimationFrame(() => setAnimateView(true));
    return () => cancelAnimationFrame(frame);
  }, [activeTab]);

  return (
    <div className="app-shell">
      <div className="ambient ambient-left" />
      <div className="ambient ambient-right" />

      <header className="topbar">
        <div className="hero-copy">
          <span className="eyebrow">Liquid Photos</span>
          <h1>Медиатека</h1>
          <p>Личная галерея, умный поиск и найденные люди в одном минималистичном интерфейсе.</p>
        </div>

        <div className="action-row">
          <button className="glass-icon-button" aria-label="Открыть поиск" onClick={() => setActiveTab('search')}>
            <SearchIcon />
          </button>
          <button className="glass-icon-button primary" aria-label="Добавить фотографии">
            <PlusIcon />
          </button>
        </div>
      </header>

      <main className={`content ${animateView ? 'content-visible' : ''}`}>
        {activeTab === 'library' && <LibraryView />}
        {activeTab === 'search' && <SearchView />}
        {activeTab === 'people' && <PeopleView />}
      </main>

      <nav className="tabbar" aria-label="Primary">
        <div className={`tab-highlight ${activeTab}`} />
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>
    </div>
  );
}

function LibraryView() {
  return (
    <section className="library-grid" aria-label="Photo library">
      {photos.map((photo) => (
        <article key={photo.id} className="photo-card">
          <img src={photo.src} alt="" />
          <div className="photo-overlay" />
        </article>
      ))}
    </section>
  );
}

function SearchView() {
  return (
    <section className="panel-view">
      <div className="glass-panel panel-large">
        <span className="panel-label">Умный поиск</span>
        <h2>Найти «девушку в очках рядом с машиной»</h2>
        <p>
          Здесь будет поиск по естественным запросам. Пока экран показывает структуру и стиль поисковой строки.
        </p>

        <div className="search-bar">
          <SearchIcon />
          <span>Опишите фото, место, предмет или человека</span>
        </div>
      </div>

      <div className="suggestions">
        {['закат у моря', 'человек с собакой', 'девушка в очках', 'ночной город'].map((item) => (
          <div key={item} className="glass-chip">
            {item}
          </div>
        ))}
      </div>
    </section>
  );
}

function PeopleView() {
  return (
    <section className="panel-view">
      <div className="glass-panel panel-large">
        <span className="panel-label">Люди</span>
        <h2>Найденные лица и группы</h2>
        <p>Позже здесь появятся сгруппированные люди и возможность присваивать им понятные имена.</p>
      </div>

      <div className="people-list">
        {people.map((person) => (
          <article key={person.id} className="glass-person-card">
            <div className="person-avatar">{person.name.slice(0, 1)}</div>
            <div>
              <h3>{person.name}</h3>
              <p>{person.hint}</p>
            </div>
            <span>{person.count} фото</span>
          </article>
        ))}
      </div>
    </section>
  );
}

function SearchIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M10.5 4a6.5 6.5 0 1 0 4.03 11.6l4.44 4.44 1.06-1.06-4.44-4.44A6.5 6.5 0 0 0 10.5 4Zm0 1.5a5 5 0 1 1 0 10 5 5 0 0 1 0-10Z"
        fill="currentColor"
      />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M11.25 5h1.5v6.25H19v1.5h-6.25V19h-1.5v-6.25H5v-1.5h6.25V5Z" fill="currentColor" />
    </svg>
  );
}

export default App;
