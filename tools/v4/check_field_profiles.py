"""Validate governed profile schema/references without requiring completed coverage.

Semantic approval and date-aware eligibility belong to public_projection. Missing,
pending and stale reviews are not structural errors and never approve a profile.
"""
import argparse
from pathlib import Path

from field_profiles import PROFILE_ROOT, ProfileContext, _load_namespace, validate_profile

ROOT = Path(__file__).resolve().parents[2]


def validate_namespace(knowledge):
    root = Path(knowledge)
    context = ProfileContext(root)
    profiles = _load_namespace(root, PROFILE_ROOT + '/records')
    reviews = _load_namespace(root, PROFILE_ROOT + '/reviews', True)
    errors = []
    for ident, profile in sorted(profiles.items()):
        codes = validate_profile(profile)
        if not codes:
            if profile['hazardId'] not in context.entities['hazards']:
                codes.append('PROFILE_HAZARD_REF_MISSING')
            for link_id in profile['basisLinkIds']:
                link = context.entities['links'].get(link_id)
                if link is None:
                    codes.append('PROFILE_LINK_REF_MISSING:' + link_id)
                elif link.get('hazardId') != profile['hazardId']:
                    codes.append('PROFILE_LINK_HAZARD_MISMATCH:' + link_id)
            # Absent upstream reviews mean unapproved, not a dangling entity.
            # All selected entity/evidence references must still resolve.
            for key, value in context.dependencies(profile, selected_only=True).items():
                if value is None and not key.startswith('reviews/'):
                    codes.append('PROFILE_DEPENDENCY_REF_MISSING:' + key)
        errors.extend(ident + ':' + code for code in sorted(set(codes)))
    return {
        'profileCount': len(profiles),
        'reviewCount': len(reviews),
        'orphanReviewCount': len(set(reviews) - set(profiles)),
        'errors': errors,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--knowledge', type=Path, default=ROOT / 'knowledge')
    args = parser.parse_args(argv)
    try:
        result = validate_namespace(args.knowledge)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print('field profiles errors: 1 (' + str(exc) + ')')
        return 1
    print('field profiles:', result['profileCount'], 'reviews:', result['reviewCount'],
          'orphan reviews:', result['orphanReviewCount'])
    print('errors:', len(result['errors']))
    for error in result['errors']:
        print(' -', error)
    print('Coverage and semantic approval are not certified by this schema/reference check.')
    return int(bool(result['errors']))


if __name__ == '__main__':
    raise SystemExit(main())
