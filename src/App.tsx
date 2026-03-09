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
  { id: 1, src: '/demo/media/media-01.jpg' },
  { id: 2, src: '/demo/media/media-02.jpg' },
  { id: 3, src: '/demo/media/media-03.jpg' },
  { id: 4, src: '/demo/media/media-04.jpg' },
  { id: 5, src: '/demo/media/media-05.jpg' },
  { id: 6, src: '/demo/media/media-06.jpg' },
  { id: 7, src: '/demo/media/media-07.jpg' },
  { id: 8, src: '/demo/media/media-08.jpg' },
  { id: 9, src: '/demo/media/media-09.jpg' },
  { id: 10, src: '/demo/media/media-10.jpg' },
  { id: 11, src: '/demo/media/media-11.jpg' },
  { id: 12, src: '/demo/media/media-12.jpg' },
];

const people = [
  {
    id: 1,
    name: 'Анна',
    count: 28,
    photo: '/demo/people/person-01.jpg',
  },
  {
    id: 2,
    name: 'Человек 2',
    count: 14,
    photo: '/demo/people/person-02.jpg',
  },
  {
    id: 3,
    name: 'Максим',
    count: 19,
    photo: '/demo/people/person-03.jpg',
  },
  {
    id: 4,
    name: 'Человек 4',
    count: 8,
    photo: '/demo/people/person-04.jpg',
  },
  {
    id: 5,
    name: 'Елена',
    count: 11,
    photo: '/demo/people/person-05.jpg',
  },
  {
    id: 6,
    name: 'Человек 6',
    count: 6,
    photo: '/demo/people/person-06.jpg',
  },
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

      <header className={`topbar ${activeTab !== 'library' ? 'topbar-compact' : ''}`}>
        {activeTab === 'library' ? (
          <div className="hero-copy">
            <span className="eyebrow">Liquid Photos</span>
            <h1>Медиатека</h1>
            <p>Личная галерея, умный поиск и найденные люди в одном минималистичном интерфейсе.</p>
          </div>
        ) : activeTab === 'people' ? (
          <div className="hero-copy people-hero-copy">
            <span className="eyebrow people-eyebrow">Liquid Photos</span>
            <h1>Люди</h1>
            <p>Лица, которые система нашла и сгруппировала по фотографиям в вашей медиатеке.</p>
          </div>
        ) : (
          <div className="topbar-spacer" />
        )}
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
    <section className="search-stage">
      <div className="search-intro">
        <span className="eyebrow search-eyebrow">Поиск</span>
        <h2>Поиск по фото</h2>
        <p>Опишите человека, объект, сцену или место на фотографии.</p>
      </div>

      <div className="search-composer">
        <div className="search-input-shell">
          <div className="search-input-placeholder">Например: девушка в очках рядом с машиной</div>

          <div className="search-toolbar">
            <button className="search-tool-button" aria-label="Добавить фильтр">
              <PlusIcon />
            </button>

            <div className="search-suggestions-inline">
              {['закат у моря', 'человек с собакой', 'ночной город'].map((item) => (
                <div key={item} className="glass-chip compact">
                  {item}
                </div>
              ))}
            </div>

            <button className="search-voice-button" aria-label="Голосовой поиск">
              <WaveIcon />
            </button>
          </div>
        </div>

        <p className="search-footnote">Позже здесь появится настоящий интеллектуальный поиск по вашей личной фотобиблиотеке.</p>
      </div>
    </section>
  );
}

function PeopleView() {
  return (
    <section className="panel-view">
      <div className="people-grid">
        {people.map((person) => (
          <article key={person.id} className="person-tile">
            <div className="person-portrait-shell">
              <img className="person-portrait" src={person.photo} alt={person.name} />
            </div>
            <span className="person-count">{person.count} фото</span>
            <h3>{person.name}</h3>
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

function WaveIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M5.5 9.25a1 1 0 0 1 1 1v3.5a1 1 0 1 1-2 0v-3.5a1 1 0 0 1 1-1Zm4-2.25a1 1 0 0 1 1 1v8a1 1 0 1 1-2 0V8a1 1 0 0 1 1-1Zm4 3a1 1 0 0 1 1 1v2a1 1 0 1 1-2 0v-2a1 1 0 0 1 1-1Zm4-4a1 1 0 0 1 1 1v10a1 1 0 1 1-2 0V7a1 1 0 0 1 1-1Z"
        fill="currentColor"
      />
    </svg>
  );
}

export default App;
