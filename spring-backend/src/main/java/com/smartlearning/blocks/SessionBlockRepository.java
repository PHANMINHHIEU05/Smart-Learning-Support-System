package com.smartlearning.blocks;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface SessionBlockRepository extends JpaRepository<SessionBlock, UUID> {

    Optional<SessionBlock> findByBlockId(UUID blockId);

    List<SessionBlock> findBySessionIdOrderByStartAtAsc(UUID sessionId);

    Optional<SessionBlock> findFirstBySessionIdOrderByStartAtDesc(UUID sessionId);
}
