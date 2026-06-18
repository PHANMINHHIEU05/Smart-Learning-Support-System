package com.smartlearning.vocab;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;

import java.time.OffsetDateTime;

@Entity
@Table(name = "vocab_lookup_cache")
public class VocabLookupCache {

    @Id
    @Column(name = "normalized_term", nullable = false, length = 255)
    private String normalizedTerm;

    @Column(name = "term", nullable = false, length = 255)
    private String term;

    @Column(name = "meaning", columnDefinition = "text")
    private String meaning;

    @Column(name = "translation_vi", columnDefinition = "text")
    private String translationVi;

    @Column(name = "definition_en", columnDefinition = "text")
    private String definitionEn;

    @Column(name = "example_sentence", columnDefinition = "text")
    private String exampleSentence;

    @Column(name = "part_of_speech", length = 80)
    private String partOfSpeech;

    @Column(name = "phonetic", length = 255)
    private String phonetic;

    @Column(name = "audio_url", columnDefinition = "text")
    private String audioUrl;

    @Column(name = "dictionary_provider", length = 100)
    private String dictionaryProvider;

    @Column(name = "translation_provider", length = 100)
    private String translationProvider;

    @Column(name = "fetched_at", nullable = false)
    private OffsetDateTime fetchedAt;

    @Column(name = "expires_at", nullable = false)
    private OffsetDateTime expiresAt;

    @Column(name = "updated_at", nullable = false)
    private OffsetDateTime updatedAt;

    @PrePersist
    void prePersist() {
        OffsetDateTime now = OffsetDateTime.now();
        if (fetchedAt == null) {
            fetchedAt = now;
        }
        if (updatedAt == null) {
            updatedAt = now;
        }
    }

    @PreUpdate
    void preUpdate() {
        updatedAt = OffsetDateTime.now();
    }

    public String getNormalizedTerm() {
        return normalizedTerm;
    }

    public void setNormalizedTerm(String normalizedTerm) {
        this.normalizedTerm = normalizedTerm;
    }

    public String getTerm() {
        return term;
    }

    public void setTerm(String term) {
        this.term = term;
    }

    public String getMeaning() {
        return meaning;
    }

    public void setMeaning(String meaning) {
        this.meaning = meaning;
    }

    public String getTranslationVi() {
        return translationVi;
    }

    public void setTranslationVi(String translationVi) {
        this.translationVi = translationVi;
    }

    public String getDefinitionEn() {
        return definitionEn;
    }

    public void setDefinitionEn(String definitionEn) {
        this.definitionEn = definitionEn;
    }

    public String getExampleSentence() {
        return exampleSentence;
    }

    public void setExampleSentence(String exampleSentence) {
        this.exampleSentence = exampleSentence;
    }

    public String getPartOfSpeech() {
        return partOfSpeech;
    }

    public void setPartOfSpeech(String partOfSpeech) {
        this.partOfSpeech = partOfSpeech;
    }

    public String getPhonetic() {
        return phonetic;
    }

    public void setPhonetic(String phonetic) {
        this.phonetic = phonetic;
    }

    public String getAudioUrl() {
        return audioUrl;
    }

    public void setAudioUrl(String audioUrl) {
        this.audioUrl = audioUrl;
    }

    public String getDictionaryProvider() {
        return dictionaryProvider;
    }

    public void setDictionaryProvider(String dictionaryProvider) {
        this.dictionaryProvider = dictionaryProvider;
    }

    public String getTranslationProvider() {
        return translationProvider;
    }

    public void setTranslationProvider(String translationProvider) {
        this.translationProvider = translationProvider;
    }

    public OffsetDateTime getFetchedAt() {
        return fetchedAt;
    }

    public void setFetchedAt(OffsetDateTime fetchedAt) {
        this.fetchedAt = fetchedAt;
    }

    public OffsetDateTime getExpiresAt() {
        return expiresAt;
    }

    public void setExpiresAt(OffsetDateTime expiresAt) {
        this.expiresAt = expiresAt;
    }
}
