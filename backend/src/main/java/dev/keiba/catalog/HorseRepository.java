package dev.keiba.catalog;

import org.springframework.data.domain.*;
import org.springframework.data.jpa.repository.JpaRepository;

interface HorseRepository extends JpaRepository<Horse, Long> {
    @org.springframework.data.jpa.repository.EntityGraph(attributePaths = { "sire", "dam" })
    Page<Horse> findByNameContainingIgnoreCase(String name, Pageable pageable);
}
