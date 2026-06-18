package com.smartlearning.vocab;

import org.junit.jupiter.api.Test;

import java.time.OffsetDateTime;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class VocabLookupCacheServiceTest {

    @Test
    void returnsValidCacheWithoutCallingWorker() {
        VocabLookupCacheRepository repository = mock(VocabLookupCacheRepository.class);
        VocabEnrichmentClient client = mock(VocabEnrichmentClient.class);
        VocabLookupCache cached = cachedEntry("resilient");
        when(repository.findByNormalizedTermAndExpiresAtAfter(eq("resilient"), any()))
                .thenReturn(Optional.of(cached));

        VocabLookupCacheService service = new VocabLookupCacheService(repository, client, 7);
        VocabEnrichmentResponse response = service.resolve("Resilient").orElseThrow();

        assertThat(response.translationVi()).isEqualTo("kiên cường");
        verify(client, never()).lookup(any(), any());
    }

    @Test
    void fetchesAndStoresCacheOnMiss() {
        VocabLookupCacheRepository repository = mock(VocabLookupCacheRepository.class);
        VocabEnrichmentClient client = mock(VocabEnrichmentClient.class);
        when(repository.findByNormalizedTermAndExpiresAtAfter(eq("resilient"), any()))
                .thenReturn(Optional.empty());
        when(client.lookup("Resilient", null)).thenReturn(Optional.of(enrichment("Resilient")));

        VocabLookupCacheService service = new VocabLookupCacheService(repository, client, 7);
        VocabEnrichmentResponse response = service.resolve("Resilient").orElseThrow();

        assertThat(response.definitionEn()).isEqualTo("able to recover quickly");
        verify(repository).save(any(VocabLookupCache.class));
    }

    @Test
    void refreshesWhenRepositoryDoesNotReturnExpiredEntry() {
        VocabLookupCacheRepository repository = mock(VocabLookupCacheRepository.class);
        VocabEnrichmentClient client = mock(VocabEnrichmentClient.class);
        when(repository.findByNormalizedTermAndExpiresAtAfter(eq("resilient"), any()))
                .thenReturn(Optional.empty());
        when(client.lookup("resilient", null)).thenReturn(Optional.of(enrichment("resilient")));

        VocabLookupCacheService service = new VocabLookupCacheService(repository, client, 7);
        assertThat(service.resolve("resilient")).isPresent();

        verify(client).lookup("resilient", null);
        verify(repository).save(any(VocabLookupCache.class));
    }

    private static VocabLookupCache cachedEntry(String term) {
        VocabLookupCache cache = new VocabLookupCache();
        cache.setNormalizedTerm(term);
        cache.setTerm(term);
        cache.setMeaning("kiên cường");
        cache.setTranslationVi("kiên cường");
        cache.setDefinitionEn("able to recover quickly");
        cache.setPartOfSpeech("adjective");
        cache.setFetchedAt(OffsetDateTime.now().minusDays(1));
        cache.setExpiresAt(OffsetDateTime.now().plusDays(6));
        return cache;
    }

    private static VocabEnrichmentResponse enrichment(String term) {
        return new VocabEnrichmentResponse(
                term,
                term.toLowerCase(),
                "kiên cường",
                "kiên cường",
                "able to recover quickly",
                null,
                "adjective",
                "/rɪˈzɪl.i.ənt/",
                "https://audio.test/resilient.mp3",
                "dictionaryapi.dev",
                "mymemory"
        );
    }
}
