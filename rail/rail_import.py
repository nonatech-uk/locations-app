#!/usr/bin/env python3
"""
Import rail journeys from JSON into the rail_journeys database table.

Reads rail-journeys.json (reconciled from SWR website + Apple Wallet passes)
and inserts with ON CONFLICT DO NOTHING for deduplication.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import db


def load_journeys(json_path):
    with open(json_path) as f:
        return json.load(f)


def import_journeys(journeys):
    conn = db.get_connection()
    cur = conn.cursor()

    inserted = 0
    skipped = 0

    for j in journeys:
        # Map price fields to single price + currency
        price = None
        currency = None
        if j.get('price_gbp'):
            price = j['price_gbp']
            currency = 'GBP'
        elif j.get('price_chf'):
            price = j['price_chf']
            currency = 'CHF'

        try:
            cur.execute("""
                INSERT INTO rail_journeys (
                    date, time, from_station, from_code, to_station, to_code,
                    operator, ticket_type, direction, reference, train, via,
                    price, currency, source
                ) VALUES (
                    %(date)s, %(time)s, %(from_station)s, %(from_code)s,
                    %(to_station)s, %(to_code)s, %(operator)s, %(ticket_type)s,
                    %(direction)s, %(reference)s, %(train)s, %(via)s,
                    %(price)s, %(currency)s, %(source)s
                )
                ON CONFLICT (date, time, from_station, to_station) DO NOTHING
            """, {
                'date': j['date'],
                'time': j.get('time'),
                'from_station': j['from_station'],
                'from_code': j.get('from_code'),
                'to_station': j['to_station'],
                'to_code': j.get('to_code'),
                'operator': j.get('operator'),
                'ticket_type': j.get('ticket_type'),
                'direction': j.get('direction'),
                'reference': j.get('reference'),
                'train': j.get('train'),
                'via': j.get('via'),
                'price': price,
                'currency': currency,
                'source': j.get('source', 'unknown'),
            })
            if cur.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"Error inserting {j['date']} {j.get('from_station')} -> {j.get('to_station')}: {e}")
            conn.rollback()
            skipped += 1
            continue

    conn.commit()
    cur.close()
    conn.close()

    return inserted, skipped


def main():
    json_path = sys.argv[1] if len(sys.argv) > 1 else '/root/rail-journeys.json'
    print(f"Loading journeys from {json_path}...")
    journeys = load_journeys(json_path)
    print(f"Found {len(journeys)} journey legs")

    print("Importing...")
    inserted, skipped = import_journeys(journeys)
    print(f"Done: {inserted} inserted, {skipped} skipped (duplicates)")


if __name__ == '__main__':
    main()
