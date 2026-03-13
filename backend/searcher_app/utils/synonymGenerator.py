from __future__ import annotations

import re
import urllib.request
from pathlib import Path

from ruwordnet import RuWordNet
import wn

from searcher_app.utils.databaseManager import DatabaseManager, KeywordSynonymRecord


RUWORDNET_DB_URL = "https://github.com/avidale/python-ruwordnet/releases/download/0.0.4/ruwordnet-2021.db"
OEWN_LEXICON = "oewn:2024"


class SynonymGenerator:
    def __init__(self, databaseManager: DatabaseManager | None = None) -> None:
        self.databaseManager = databaseManager
        self.wordnet = self._loadWordNet()
        self.englishWordnet = self._loadEnglishWordNet()

    def generateSynonyms(self, word: str) -> list[str]:
        normalizedWord = self.normalizeWord(word)
        if not normalizedWord:
            return []

        cachedSynonyms = self.getCachedSynonyms(normalizedWord)
        if cachedSynonyms:
            return cachedSynonyms

        if self._isEnglishWord(normalizedWord):
            synonyms = self._getEnglishSynonyms(normalizedWord)
        else:
            synonyms = self._getRussianSynonyms(normalizedWord)

        uniqueSynonyms = self._deduplicateWords([normalizedWord, *synonyms])
        self.saveSynonyms(normalizedWord, uniqueSynonyms)
        return uniqueSynonyms

    def normalizeWord(self, word: str) -> str:
        return re.sub(r"\s+", " ", word.strip().lower())

    def getCachedSynonyms(self, normalizedWord: str) -> list[str]:
        if self.databaseManager is None:
            return []

        cachedRecords = self.databaseManager.getSynonyms(normalizedWord)
        if not cachedRecords:
            return []

        synonyms = [normalizedWord]
        synonyms.extend(record.synonymWord for record in cachedRecords)
        return self._deduplicateWords(synonyms)

    def saveSynonyms(self, normalizedWord: str, synonyms: list[str]) -> None:
        if self.databaseManager is None:
            return

        for synonym in synonyms:
            if synonym == normalizedWord:
                continue
            self.databaseManager.addSynonym(
                KeywordSynonymRecord(
                    id=None,
                    baseWord=normalizedWord,
                    normalizedBaseWord=normalizedWord,
                    synonymWord=synonym,
                    normalizedSynonymWord=self.normalizeWord(synonym),
                    source="wordnet",
                )
            )

    def _getRussianSynonyms(self, word: str) -> list[str]:
        synonyms: list[str] = []
        for sense in self.wordnet.get_senses(word):
            for synonymSense in sense.synset.senses:
                candidate = self.normalizeWord(synonymSense.name.replace("_", " "))
                if candidate:
                    synonyms.append(candidate)
        return synonyms

    def _getEnglishSynonyms(self, word: str) -> list[str]:
        synonyms: list[str] = []
        selectedSynsets = self._selectEnglishSynsets(word)
        for synset in selectedSynsets:
            for wordForm in synset.words():
                candidate = self.normalizeWord(wordForm.lemma().replace("_", " "))
                if not candidate or candidate == word:
                    continue
                if self._shouldSkipEnglishCandidate(candidate):
                    continue
                synonyms.append(candidate)
        return synonyms

    def _loadWordNet(self) -> RuWordNet:
        try:
            return RuWordNet()
        except FileNotFoundError:
            self._downloadWordNetDatabase()
            return RuWordNet()

    def _downloadWordNetDatabase(self) -> None:
        import ruwordnet

        staticDir = Path(ruwordnet.__file__).resolve().parent / "static"
        staticDir.mkdir(parents=True, exist_ok=True)
        destination = staticDir / "ruwordnet.db"
        urllib.request.urlretrieve(RUWORDNET_DB_URL, destination)

    def _loadEnglishWordNet(self) -> wn.Wordnet:
        try:
            return wn.Wordnet(OEWN_LEXICON)
        except wn.Error:
            wn.download(OEWN_LEXICON)
            return wn.Wordnet(OEWN_LEXICON)

    def _selectEnglishSynsets(self, word: str) -> list:
        adjectiveSynsets = self.englishWordnet.synsets(word, pos="a")
        satelliteSynsets = self.englishWordnet.synsets(word, pos="s")
        nounSynsets = self.englishWordnet.synsets(word, pos="n")

        if adjectiveSynsets or satelliteSynsets:
            return [*adjectiveSynsets[:2], *satelliteSynsets[:1]]

        if nounSynsets:
            preferredNounSynset = self._pickPreferredEnglishNounSynset(word, nounSynsets)
            return [preferredNounSynset]

        fallbackSynsets = self.englishWordnet.synsets(word)
        return fallbackSynsets[:1]

    def _shouldSkipEnglishCandidate(self, candidate: str) -> bool:
        if len(candidate) <= 1:
            return True
        if candidate.isupper():
            return True
        if any(char.isdigit() for char in candidate):
            return True
        return False

    def _pickPreferredEnglishNounSynset(self, word: str, nounSynsets: list) -> object:
        normalizedWord = self.normalizeWord(word)
        for synset in nounSynsets:
            words = synset.words()
            if not words:
                continue
            firstLemma = self.normalizeWord(words[0].lemma().replace("_", " "))
            if firstLemma == normalizedWord:
                return synset
        return nounSynsets[0]

    def _isEnglishWord(self, word: str) -> bool:
        return bool(word) and all("a" <= char <= "z" or char in {" ", "-"} for char in word)

    def _deduplicateWords(self, words: list[str]) -> list[str]:
        uniqueWords: list[str] = []
        seenWords: set[str] = set()
        for word in words:
            normalizedWord = self.normalizeWord(word)
            if not normalizedWord or normalizedWord in seenWords:
                continue
            seenWords.add(normalizedWord)
            uniqueWords.append(normalizedWord)
        return uniqueWords
