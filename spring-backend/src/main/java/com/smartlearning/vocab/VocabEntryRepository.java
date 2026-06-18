package com.smartlearning.vocab;

import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface VocabEntryRepository extends JpaRepository<VocabEntry, UUID> {

    Optional<VocabEntry> findByVocabIdAndUserId(UUID vocabId, UUID userId);

    Optional<VocabEntry> findByUserIdAndTermIgnoreCase(UUID userId, String term);

    List<VocabEntry> findByUserIdOrderByCreatedAtDesc(UUID userId, Pageable pageable);

    List<VocabEntry> findByUserIdAndStatusOrderByCreatedAtDesc(UUID userId, VocabStatus status, Pageable pageable);

    List<VocabEntry> findByUserIdAndNextReviewAtLessThanEqualAndStatusNotOrderByNextReviewAtAsc(
            UUID userId,
            OffsetDateTime dueAt,
            VocabStatus status,
            Pageable pageable
    );

    boolean existsByUserIdAndTermIgnoreCase(UUID userId, String term);
}
