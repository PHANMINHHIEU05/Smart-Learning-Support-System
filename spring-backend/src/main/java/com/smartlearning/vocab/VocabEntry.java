package com.smartlearning.vocab;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;

import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.UUID;

@Entity
@Table(name = "vocab_library")
public class VocabEntry {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "vocab_id", nullable = false)
    private UUID vocabId;

    @Column(name = "user_id", nullable = false)
    private UUID userId;

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

    @Column(name = "collocation", columnDefinition = "text")
    private String collocation;

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

    @Column(name = "source_type", length = 40)
    private String sourceType;

    @Column(name = "source_ref", columnDefinition = "text")
    private String sourceRef;

    @Column(name = "status", nullable = false, length = 30)
    private VocabStatus status = VocabStatus.NOT_STARTED;

    @Column(name = "ease_factor", nullable = false, precision = 4, scale = 2)
    private BigDecimal easeFactor = BigDecimal.valueOf(2.50);

    @Column(name = "interval_days", nullable = false)
    private Integer intervalDays = 0;

    @Column(name = "repetition_count", nullable = false)
    private Integer repetitionCount = 0;

    @Column(name = "study_box", nullable = false)
    private Integer studyBox = 1;

    @Column(name = "next_review_at", nullable = false)
    private OffsetDateTime nextReviewAt;

    @Column(name = "last_reviewed_at")
    private OffsetDateTime lastReviewedAt;

    @Column(name = "created_at", nullable = false)
    private OffsetDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private OffsetDateTime updatedAt;

    @PrePersist
    void prePersist() {
        OffsetDateTime now = OffsetDateTime.now();
        if (createdAt == null) {
            createdAt = now;
        }
        if (updatedAt == null) {
            updatedAt = now;
        }
        if (nextReviewAt == null) {
            nextReviewAt = now;
        }
        if (status == null) {
            status = VocabStatus.NOT_STARTED;
        }
        if (easeFactor == null) {
            easeFactor = BigDecimal.valueOf(2.50);
        }
        if (intervalDays == null) {
            intervalDays = 0;
        }
        if (repetitionCount == null) {
            repetitionCount = 0;
        }
        if (studyBox == null) {
            studyBox = 1;
        }
    }

    @PreUpdate
    void preUpdate() {
        updatedAt = OffsetDateTime.now();
    }

    public UUID getVocabId() {
        return vocabId;
    }

    public UUID getUserId() {
        return userId;
    }

    public void setUserId(UUID userId) {
        this.userId = userId;
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

    public String getCollocation() {
        return collocation;
    }

    public void setCollocation(String collocation) {
        this.collocation = collocation;
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

    public String getSourceType() {
        return sourceType;
    }

    public void setSourceType(String sourceType) {
        this.sourceType = sourceType;
    }

    public String getSourceRef() {
        return sourceRef;
    }

    public void setSourceRef(String sourceRef) {
        this.sourceRef = sourceRef;
    }

    public VocabStatus getStatus() {
        return status;
    }

    public void setStatus(VocabStatus status) {
        this.status = status;
    }

    public BigDecimal getEaseFactor() {
        return easeFactor;
    }

    public void setEaseFactor(BigDecimal easeFactor) {
        this.easeFactor = easeFactor;
    }

    public Integer getIntervalDays() {
        return intervalDays;
    }

    public void setIntervalDays(Integer intervalDays) {
        this.intervalDays = intervalDays;
    }

    public Integer getRepetitionCount() {
        return repetitionCount;
    }

    public void setRepetitionCount(Integer repetitionCount) {
        this.repetitionCount = repetitionCount;
    }

    public Integer getStudyBox() {
        return studyBox;
    }

    public void setStudyBox(Integer studyBox) {
        this.studyBox = studyBox;
    }

    public OffsetDateTime getNextReviewAt() {
        return nextReviewAt;
    }

    public void setNextReviewAt(OffsetDateTime nextReviewAt) {
        this.nextReviewAt = nextReviewAt;
    }

    public OffsetDateTime getLastReviewedAt() {
        return lastReviewedAt;
    }

    public void setLastReviewedAt(OffsetDateTime lastReviewedAt) {
        this.lastReviewedAt = lastReviewedAt;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }

    public OffsetDateTime getUpdatedAt() {
        return updatedAt;
    }
}
