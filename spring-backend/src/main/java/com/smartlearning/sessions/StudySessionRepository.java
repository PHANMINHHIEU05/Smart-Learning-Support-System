package com.smartlearning.sessions;

import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface StudySessionRepository extends JpaRepository<StudySession, UUID> {

    Optional<StudySession> findBySessionIdAndUserId(UUID sessionId, UUID userId);

    List<StudySession> findByUserIdOrderByStartedAtDesc(UUID userId, Pageable pageable);

    List<StudySession> findByUserIdAndStartedAtGreaterThanEqualAndStartedAtLessThanEqualOrderByStartedAtDesc(
            UUID userId,
            OffsetDateTime dateFrom,
            OffsetDateTime dateTo,
            Pageable pageable
    );
}
