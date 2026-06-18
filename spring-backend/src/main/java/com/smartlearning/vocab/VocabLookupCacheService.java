package com.smartlearning.vocab;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.Optional;

@Service
public class VocabLookupCacheService {

    private final VocabLookupCacheRepository repository;
    private final VocabEnrichmentClient enrichmentClient;
    private final long ttlDays;

    public VocabLookupCacheService(
            VocabLookupCacheRepository repository,
            VocabEnrichmentClient enrichmentClient,
            @Value("${app.vocabulary.cache-ttl-days:7}") long ttlDays
    ) {
        this.repository = repository;
        this.enrichmentClient = enrichmentClient;
        this.ttlDays = Math.max(1, ttlDays);
    }

    @Transactional
    public Optional<VocabEnrichmentResponse> resolve(String term) {
        String normalizedTerm = term.trim().toLowerCase();
        OffsetDateTime now = OffsetDateTime.now();

        Optional<VocabLookupCache> cached = repository
                .findByNormalizedTermAndExpiresAtAfter(normalizedTerm, now);
        if (cached.isPresent()) {
            return cached.map(VocabLookupCacheService::toResponse);
        }

        Optional<VocabEnrichmentResponse> fetched = enrichmentClient.lookup(term, null);
        fetched.ifPresent(response -> repository.save(toEntity(response, term, normalizedTerm, now)));
        return fetched;
    }

    private VocabLookupCache toEntity(
            VocabEnrichmentResponse response,
            String requestedTerm,
            String normalizedTerm,
            OffsetDateTime fetchedAt
    ) {
        VocabLookupCache cache = new VocabLookupCache();
        cache.setNormalizedTerm(normalizedTerm);
        cache.setTerm(firstNonBlank(response.term(), requestedTerm));
        cache.setMeaning(response.meaning());
        cache.setTranslationVi(response.translationVi());
        cache.setDefinitionEn(response.definitionEn());
        cache.setExampleSentence(response.exampleSentence());
        cache.setPartOfSpeech(response.partOfSpeech());
        cache.setPhonetic(response.phonetic());
        cache.setAudioUrl(response.audioUrl());
        cache.setDictionaryProvider(response.dictionaryProvider());
        cache.setTranslationProvider(response.translationProvider());
        cache.setFetchedAt(fetchedAt);
        cache.setExpiresAt(fetchedAt.plusDays(ttlDays));
        return cache;
    }

    private static VocabEnrichmentResponse toResponse(VocabLookupCache cache) {
        return new VocabEnrichmentResponse(
                cache.getTerm(),
                cache.getNormalizedTerm(),
                cache.getMeaning(),
                cache.getTranslationVi(),
                cache.getDefinitionEn(),
                cache.getExampleSentence(),
                cache.getPartOfSpeech(),
                cache.getPhonetic(),
                cache.getAudioUrl(),
                cache.getDictionaryProvider(),
                cache.getTranslationProvider()
        );
    }

    private static String firstNonBlank(String first, String second) {
        return first != null && !first.isBlank() ? first.trim() : second.trim();
    }
}
