"""
Infrastructure Dependency and Impact Analysis.

Performs deterministic graph traversal over HIMP's canonical
asset_relationships contract.

Dependency traversal follows relationship edges from source to target.
Impact traversal follows relationship edges in reverse, from target
to source.

The service is read-only. It does not create, modify, or infer
infrastructure relationships.
"""

from dataclasses import asdict

from himp.services.asset_relationships import (
    AssetRelationshipService,
)


class DependencyImpactService:
    """
    Traverse canonical infrastructure relationships deterministically.

    Each returned node records:
    - entity_type
    - entity_id
    - depth
    - relationship path from the requested root

    Traversal is cycle-safe and returns each reachable entity once,
    using the shortest discovered path.
    """

    def __init__(
        self,
        relationships=None,
    ):
        self.relationships = (
            relationships
            or AssetRelationshipService()
        )

    def _validate_root(
        self,
        entity_type,
        entity_id,
    ):
        return self.relationships._validate_entity(
            entity_type,
            entity_id,
        )

    @staticmethod
    def _entity_key(
        entity_type,
        entity_id,
    ):
        return (
            entity_type,
            entity_id,
        )

    @staticmethod
    def _edge_dict(
        relationship,
    ):
        return asdict(
            relationship
        )

    @staticmethod
    def _sort_relationships(
        relationships,
    ):
        return sorted(
            relationships,
            key=lambda item: (
                item.relationship_type,
                item.source_type,
                item.source_id,
                item.target_type,
                item.target_id,
            ),
        )

    def dependencies(
        self,
        entity_type,
        entity_id,
        max_depth=None,
    ):
        """
        Return assets reachable by following outgoing relationships.

        Answers:
            "What does this asset depend on?"

        max_depth:
            None means unbounded traversal.
            Positive integers limit returned traversal depth.
        """
        entity_type, entity_id = (
            self._validate_root(
                entity_type,
                entity_id,
            )
        )

        max_depth = self._validate_depth(
            max_depth
        )

        root_key = self._entity_key(
            entity_type,
            entity_id,
        )

        visited = {
            root_key
        }

        queue = [
            (
                entity_type,
                entity_id,
                0,
                [],
            )
        ]

        results = []

        while queue:
            (
                current_type,
                current_id,
                current_depth,
                path,
            ) = queue.pop(0)

            if (
                max_depth is not None
                and current_depth >= max_depth
            ):
                continue

            relationships = (
                self.relationships.list_for_source(
                    source_type=current_type,
                    source_id=current_id,
                )
            )

            for relationship in self._sort_relationships(
                relationships
            ):
                target_key = self._entity_key(
                    relationship.target_type,
                    relationship.target_id,
                )

                if target_key in visited:
                    continue

                visited.add(
                    target_key
                )

                depth = current_depth + 1

                edge = self._edge_dict(
                    relationship
                )

                target_path = [
                    *path,
                    edge,
                ]

                results.append(
                    {
                        "entity_type": (
                            relationship.target_type
                        ),
                        "entity_id": (
                            relationship.target_id
                        ),
                        "depth": depth,
                        "via_relationship": (
                            relationship.relationship_type
                        ),
                        "path": target_path,
                    }
                )

                queue.append(
                    (
                        relationship.target_type,
                        relationship.target_id,
                        depth,
                        target_path,
                    )
                )

        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "direction": "dependencies",
            "count": len(results),
            "max_depth": max_depth,
            "assets": results,
        }

    def impact(
        self,
        entity_type,
        entity_id,
        max_depth=None,
    ):
        """
        Return assets reachable by following relationships in reverse.

        Answers:
            "What depends on this asset?"
            "What could be affected if this asset fails?"

        max_depth:
            None means unbounded traversal.
            Positive integers limit returned traversal depth.
        """
        entity_type, entity_id = (
            self._validate_root(
                entity_type,
                entity_id,
            )
        )

        max_depth = self._validate_depth(
            max_depth
        )

        root_key = self._entity_key(
            entity_type,
            entity_id,
        )

        visited = {
            root_key
        }

        queue = [
            (
                entity_type,
                entity_id,
                0,
                [],
            )
        ]

        results = []

        while queue:
            (
                current_type,
                current_id,
                current_depth,
                path,
            ) = queue.pop(0)

            if (
                max_depth is not None
                and current_depth >= max_depth
            ):
                continue

            relationships = (
                self.relationships.list_for_target(
                    target_type=current_type,
                    target_id=current_id,
                )
            )

            for relationship in self._sort_relationships(
                relationships
            ):
                source_key = self._entity_key(
                    relationship.source_type,
                    relationship.source_id,
                )

                if source_key in visited:
                    continue

                visited.add(
                    source_key
                )

                depth = current_depth + 1

                edge = self._edge_dict(
                    relationship
                )

                source_path = [
                    *path,
                    edge,
                ]

                results.append(
                    {
                        "entity_type": (
                            relationship.source_type
                        ),
                        "entity_id": (
                            relationship.source_id
                        ),
                        "depth": depth,
                        "via_relationship": (
                            relationship.relationship_type
                        ),
                        "path": source_path,
                    }
                )

                queue.append(
                    (
                        relationship.source_type,
                        relationship.source_id,
                        depth,
                        source_path,
                    )
                )

        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "direction": "impact",
            "count": len(results),
            "max_depth": max_depth,
            "assets": results,
        }

    @staticmethod
    def _validate_depth(
        max_depth,
    ):
        if max_depth is None:
            return None

        if (
            isinstance(max_depth, bool)
            or not isinstance(max_depth, int)
            or max_depth < 1
        ):
            raise ValueError(
                "max_depth must be a positive integer"
            )

        return max_depth
