package com.smartlearning.vocab;

import org.springframework.data.jpa.repository.JpaRepository;

import java.time.OffsetDateTime;
import java.util.Optional;

public interface VocabLookupCacheRepository extends JpaRepository<VocabLookupCache, String> {

    Optional<VocabLookupCache> findByNormalizedTermAndExpiresAtAfter(
            String normalizedTerm,
            OffsetDateTime now
    );
}
