package com.smartlearning.tasks;

import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface TaskRepository extends JpaRepository<Task, UUID> {

    Optional<Task> findByTaskIdAndUserId(UUID taskId, UUID userId);

    List<Task> findByUserIdOrderByCreatedAtDesc(UUID userId, Pageable pageable);

    List<Task> findByUserIdAndStatusOrderByCreatedAtDesc(UUID userId, TaskStatus status, Pageable pageable);

    List<Task> findByUserIdAndDueAtGreaterThanEqualAndDueAtLessThanEqualOrderByCreatedAtDesc(
            UUID userId,
            OffsetDateTime dueFrom,
            OffsetDateTime dueTo,
            Pageable pageable
    );

    List<Task> findByUserIdAndStatusAndDueAtGreaterThanEqualAndDueAtLessThanEqualOrderByCreatedAtDesc(
            UUID userId,
            TaskStatus status,
            OffsetDateTime dueFrom,
            OffsetDateTime dueTo,
            Pageable pageable
    );
}
