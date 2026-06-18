package com.smartlearning.vocab;

import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

@Service
public class VocabService {

    private static final BigDecimal MIN_EASE = BigDecimal.valueOf(1.30);
    private static final BigDecimal MAX_EASE = BigDecimal.valueOf(4.00);
    private static final BigDecimal DEFAULT_EASE = BigDecimal.valueOf(2.50);

    private final VocabEntryRepository repository;
    private final VocabEnrichmentClient enrichmentClient;

    public VocabService(VocabEntryRepository repository, VocabEnrichmentClient enrichmentClient) {
        this.repository = repository;
        this.enrichmentClient = enrichmentClient;
    }

    @Transactional
    public VocabEntryResponse create(UUID userId, CreateVocabRequest request) {
        String term = normalizeTerm(request.term());
        ensureTermAvailable(userId, term);

        VocabEntry entry = new VocabEntry();
        entry.setUserId(userId);
        entry.setTerm(term);
        entry.setMeaning(request.meaning());
        entry.setExampleSentence(request.exampleSentence());
        entry.setSourceType(request.sourceType());
        entry.setSourceRef(request.sourceRef());
        entry.setStatus(request.status() == null ? VocabStatus.NOT_STARTED : request.status());
        if (request.nextReviewAt() != null) {
            entry.setNextReviewAt(request.nextReviewAt());
        }

        return VocabEntryResponse.from(repository.save(entry));
    }

    @Transactional(readOnly = true)
    public VocabLookupResponse lookup(UUID userId, VocabLookupRequest request) {
        String term = normalizeTerm(request.term());
        ensureTermNotBlank(term);
        boolean alreadySaved = repository.existsByUserIdAndTermIgnoreCase(userId, term);
        VocabEnrichmentResponse enrichment = enrichmentClient.lookup(term, request.contextSentence()).orElse(null);
        String normalizedTerm = enrichment == null
                ? term
                : firstNonBlank(enrichment.normalizedTerm(), term);
        String exampleSentence = enrichment == null
                ? firstNonBlank(request.contextSentence(), term)
                : firstNonBlank(enrichment.exampleSentence(), request.contextSentence());
        String sourceRef = firstNonBlank(request.pageUrl(), request.pageTitle());

        return new VocabLookupResponse(
                term,
                normalizedTerm,
                enrichment == null ? null : enrichment.meaning(),
                enrichment == null ? null : enrichment.translationVi(),
                enrichment == null ? null : enrichment.definitionEn(),
                exampleSentence,
                enrichment == null ? null : enrichment.partOfSpeech(),
                enrichment == null ? null : enrichment.phonetic(),
                enrichment == null ? null : enrichment.audioUrl(),
                enrichment == null ? null : enrichment.dictionaryProvider(),
                enrichment == null ? null : enrichment.translationProvider(),
                "firefox_extension",
                sourceRef,
                alreadySaved
        );
    }

    @Transactional
    public VocabEntryResponse capture(UUID userId, VocabCaptureRequest request) {
        String term = normalizeTerm(request.term());
        ensureTermNotBlank(term);

        return repository.findByUserIdAndTermIgnoreCase(userId, term)
                .map(VocabEntryResponse::from)
                .orElseGet(() -> {
                    VocabEntry entry = new VocabEntry();
                    entry.setUserId(userId);
                    entry.setTerm(term);
                    entry.setMeaning(blankToNull(request.meaning()));
                    entry.setExampleSentence(blankToNull(firstNonBlank(request.exampleSentence(), request.contextSentence())));
                    entry.setSourceType("firefox_extension");
                    entry.setSourceRef(blankToNull(firstNonBlank(request.pageUrl(), request.pageTitle())));
                    entry.setStatus(VocabStatus.NOT_STARTED);
                    return VocabEntryResponse.from(repository.save(entry));
                });
    }

    @Transactional(readOnly = true)
    public List<VocabEntryResponse> list(UUID userId, VocabStatus status, int offset, int limit) {
        Pageable pageable = PageRequest.of(offset / limit, limit);
        List<VocabEntry> entries = status == null
                ? repository.findByUserIdOrderByCreatedAtDesc(userId, pageable)
                : repository.findByUserIdAndStatusOrderByCreatedAtDesc(userId, status, pageable);
        return entries.stream().map(VocabEntryResponse::from).toList();
    }

    @Transactional(readOnly = true)
    public List<VocabEntryResponse> due(UUID userId, OffsetDateTime now, int limit) {
        Pageable pageable = PageRequest.of(0, limit);
        return repository.findByUserIdAndNextReviewAtLessThanEqualAndStatusNotOrderByNextReviewAtAsc(
                        userId,
                        now == null ? OffsetDateTime.now() : now,
                        VocabStatus.ARCHIVED,
                        pageable
                )
                .stream()
                .map(VocabEntryResponse::from)
                .toList();
    }

    @Transactional
    public VocabEntryResponse update(UUID userId, UUID vocabId, UpdateVocabRequest request) {
        VocabEntry entry = getOwnedEntry(userId, vocabId);

        if (request.term() != null) {
            String term = normalizeTerm(request.term());
            ensureTermNotBlank(term);
            if (!term.equalsIgnoreCase(entry.getTerm())) {
                ensureTermAvailable(userId, term);
            }
            entry.setTerm(term);
        }
        if (request.meaning() != null) {
            entry.setMeaning(request.meaning());
        }
        if (request.exampleSentence() != null) {
            entry.setExampleSentence(request.exampleSentence());
        }
        if (request.sourceType() != null) {
            entry.setSourceType(request.sourceType());
        }
        if (request.sourceRef() != null) {
            entry.setSourceRef(request.sourceRef());
        }
        if (request.status() != null) {
            entry.setStatus(request.status());
        }
        if (request.nextReviewAt() != null) {
            entry.setNextReviewAt(request.nextReviewAt());
        }

        return VocabEntryResponse.from(repository.save(entry));
    }

    @Transactional
    public VocabEntryResponse review(UUID userId, UUID vocabId, ReviewVocabRequest request) {
        VocabEntry entry = getOwnedEntry(userId, vocabId);
        OffsetDateTime reviewedAt = request.reviewedAt() == null ? OffsetDateTime.now() : request.reviewedAt();
        applySrs(entry, request.quality(), reviewedAt);
        return VocabEntryResponse.from(repository.save(entry));
    }

    @Transactional
    public void delete(UUID userId, UUID vocabId) {
        VocabEntry entry = getOwnedEntry(userId, vocabId);
        repository.delete(entry);
    }

    private VocabEntry getOwnedEntry(UUID userId, UUID vocabId) {
        return repository.findByVocabIdAndUserId(vocabId, userId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Vocabulary entry not found"));
    }

    private void applySrs(VocabEntry entry, ReviewQuality quality, OffsetDateTime reviewedAt) {
        BigDecimal ease = entry.getEaseFactor() == null ? DEFAULT_EASE : entry.getEaseFactor();
        int currentInterval = entry.getIntervalDays() == null ? 0 : entry.getIntervalDays();
        int currentRepetition = entry.getRepetitionCount() == null ? 0 : entry.getRepetitionCount();

        int nextInterval;
        int nextRepetition = currentRepetition;
        VocabStatus nextStatus;

        switch (quality) {
            case HARD -> {
                ease = clampEase(ease.subtract(BigDecimal.valueOf(0.20)));
                nextInterval = 1;
                nextRepetition = 0;
                nextStatus = VocabStatus.LEARNING;
            }
            case FUZZY -> {
                ease = clampEase(ease.subtract(BigDecimal.valueOf(0.10)));
                nextInterval = Math.max(1, (int) Math.ceil(Math.max(1, currentInterval) * 1.2));
                nextStatus = VocabStatus.FUZZY;
            }
            case REMEMBERED -> {
                nextRepetition = currentRepetition + 1;
                nextInterval = nextRepetition == 1
                        ? 1
                        : nextRepetition == 2
                        ? 3
                        : Math.max(3, (int) Math.round(Math.max(1, currentInterval) * ease.doubleValue()));
                nextStatus = VocabStatus.REMEMBERED;
            }
            case EASY -> {
                ease = clampEase(ease.add(BigDecimal.valueOf(0.15)));
                nextRepetition = currentRepetition + 1;
                nextInterval = currentInterval < 4
                        ? 4
                        : Math.max(4, (int) Math.round(currentInterval * ease.doubleValue()));
                nextStatus = VocabStatus.MASTERED;
            }
            default -> throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Unsupported review quality");
        }

        entry.setEaseFactor(ease.setScale(2, RoundingMode.HALF_UP));
        entry.setIntervalDays(nextInterval);
        entry.setRepetitionCount(nextRepetition);
        entry.setStatus(nextStatus);
        entry.setLastReviewedAt(reviewedAt);
        entry.setNextReviewAt(reviewedAt.plusDays(nextInterval));
    }

    private void ensureTermAvailable(UUID userId, String term) {
        if (repository.existsByUserIdAndTermIgnoreCase(userId, term)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Vocabulary term already exists");
        }
    }

    private void ensureTermNotBlank(String term) {
        if (term.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Vocabulary term must not be blank");
        }
    }

    private static String normalizeTerm(String term) {
        return term == null ? "" : term.trim();
    }

    private static String firstNonBlank(String first, String second) {
        if (first != null && !first.isBlank()) {
            return first.trim();
        }
        if (second != null && !second.isBlank()) {
            return second.trim();
        }
        return null;
    }

    private static String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }

    private static BigDecimal clampEase(BigDecimal ease) {
        if (ease.compareTo(MIN_EASE) < 0) {
            return MIN_EASE;
        }
        if (ease.compareTo(MAX_EASE) > 0) {
            return MAX_EASE;
        }
        return ease;
    }
}
