#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Numeric Dataset Generator for Top-K MapReduce Task
Generates text datasets containing random integers so the Hadoop job can output the top-K maximum numbers.
Usage: python3 generate_data.py <size_in_mb> [options]
"""

import argparse
import os
import random
from datetime import datetime


class DatasetGenerator:
    def __init__(self, min_value=0, max_value=1_000_000_000, numbers_per_line=8, spike_chance=0.02):
        self.min_value = min_value
        self.max_value = max_value
        self.numbers_per_line = numbers_per_line
        self.spike_chance = spike_chance
        self.spike_max = max_value * 10  # occasionally emit extra-large numbers to test top-K

    def generate_number(self):
        """Generate a single random number with occasional large spikes."""
        if random.random() < self.spike_chance:
            return random.randint(self.max_value, self.spike_max)
        return random.randint(self.min_value, self.max_value)

    def generate_line(self):
        """Generate one line containing multiple integers separated by spaces."""
        numbers = (str(self.generate_number()) for _ in range(self.numbers_per_line))
        return " ".join(numbers)

    def generate_file(self, filepath, target_size_mb, progress_callback=None):
        """Generate a single file with the specified size in MB."""
        target_size_bytes = target_size_mb * 1024 * 1024
        current_size = 0
        lines_written = 0

        with open(filepath, 'w', encoding='utf-8') as f:
            while current_size < target_size_bytes:
                line = self.generate_line()
                f.write(line + '\n')
                current_size += len(line.encode('utf-8')) + 1  # +1 for newline
                lines_written += 1

                if progress_callback and lines_written % 1_000_000 == 0:
                    progress_pct = min(100, (current_size / target_size_bytes) * 100)
                    progress_callback(filepath, progress_pct, current_size, lines_written)

        return current_size, lines_written

    def calculate_optimal_files(self, total_size_mb):
        """Calculate optimal number of files based on dataset size."""
        if total_size_mb <= 5:
            return 2
        elif total_size_mb <= 50:
            return 4
        elif total_size_mb <= 500:
            return 8
        else:
            return max(16, min(32, total_size_mb // 100))

    def generate_dataset(self, total_size_mb, output_dir=None, num_files=None, prefix='data'):
        """Generate a complete dataset containing random integers."""
        if output_dir is None:
            if total_size_mb <= 5:
                output_dir = 'input-local'
            elif total_size_mb <= 100:
                output_dir = 'input-small'
            else:
                output_dir = 'input-large'

        if num_files is None:
            num_files = self.calculate_optimal_files(total_size_mb)

        size_per_file_mb = total_size_mb / num_files

        print(f"=== Generating {total_size_mb}MB numeric dataset ===")
        print(f"Output directory: {output_dir}")
        print(f"Number of files: {num_files}")
        print(f"Target size per file: {size_per_file_mb:.2f}MB")
        print(f"Numbers per line: {self.numbers_per_line}, value range: [{self.min_value}, {self.max_value}]")

        os.makedirs(output_dir, exist_ok=True)

        total_bytes = 0
        total_lines = 0
        start_time = datetime.now()

        def progress_callback(filepath, progress_pct, current_size, lines_written):
            print(f"  {os.path.basename(filepath)}: {progress_pct:.1f}% ({current_size/1024/1024:.1f}MB, {lines_written:,} lines)")

        for i in range(num_files):
            filename = f"{prefix}{i + 1:02d}.txt"
            filepath = os.path.join(output_dir, filename)

            print(f"\nGenerating file {i + 1}/{num_files}: {filename}")
            file_size, file_lines = self.generate_file(filepath, size_per_file_mb, progress_callback)

            total_bytes += file_size
            total_lines += file_lines

            actual_size_mb = file_size / 1024 / 1024
            print(f"  ✓ Completed: {actual_size_mb:.2f}MB, {file_lines:,} lines")

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print(f"\n🎉 Dataset generation completed!")
        print(f"Total size: {total_bytes/1024/1024:.3f}MB ({total_bytes:,} bytes)")
        print(f"Total lines: {total_lines:,}")
        print(f"Generation time: {duration:.2f} seconds")
        if duration > 0:
            print(f"Average speed: {(total_bytes/1024/1024)/duration:.2f} MB/s")

        self.create_hdfs_upload_script(output_dir, num_files, prefix)

        return output_dir, total_bytes, total_lines

    def create_hdfs_upload_script(self, output_dir, num_files, prefix):
        """Create a helper script to upload generated files to HDFS."""
        upload_script_path = os.path.join(output_dir, 'upload_to_hdfs.sh')

        if 'local' in output_dir:
            default_hdfs_path = '/mr_input_local'
        elif 'small' in output_dir:
            default_hdfs_path = '/mr_input_small'
        else:
            default_hdfs_path = '/mr_input'

        with open(upload_script_path, 'w') as f:
            f.write('#!/bin/bash\n\n')
            f.write('# Upload generated dataset to HDFS\n')
            f.write('# Usage: ./upload_to_hdfs.sh [hdfs_path]\n\n')
            f.write(f'HDFS_PATH=${{1:-"{default_hdfs_path}"}}\n\n')
            f.write('echo "Creating HDFS directory: $HDFS_PATH"\n')
            f.write('hdfs dfs -mkdir -p "$HDFS_PATH"\n\n')
            f.write('echo "Uploading dataset files..."\n')
            for i in range(num_files):
                filename = f"{prefix}{i + 1:02d}.txt"
                f.write(f'hdfs dfs -put -f "{filename}" "$HDFS_PATH/"\n')
            f.write('\necho "Upload completed. Verifying..."\n')
            f.write('hdfs dfs -ls "$HDFS_PATH"\n')
            f.write('hdfs dfs -du -h "$HDFS_PATH"\n')

        os.chmod(upload_script_path, 0o755)

        print(f"\n📝 Additional files created:")
        print(f"  - HDFS upload script: {upload_script_path}")
        print(f"\n🚀 Next steps:")
        print(f"  1. Upload to HDFS: cd {output_dir} && ./upload_to_hdfs.sh")
        print(f"  2. Run experiments: ./monitor_job.sh 0.3 {default_hdfs_path} /mr_output")


def main():
    parser = argparse.ArgumentParser(
        description='Generate numeric datasets for Top-K MapReduce experiments',
        epilog="""
Examples:
  python3 generate_data.py 1                # Generate 1MB dataset
  python3 generate_data.py 100 --per-line 4 # Generate 100MB dataset with 4 numbers per line
  python3 generate_data.py 50 --min 0 --max 1000000
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('size', type=int, help='Dataset size in MB')
    parser.add_argument('--files', type=int, help='Number of files to generate (auto-calculated if not specified)')
    parser.add_argument('--output', type=str, help='Output directory (auto-determined if not specified)')
    parser.add_argument('--prefix', type=str, default='data', help='File prefix (default: data)')
    parser.add_argument('--min', dest='min_value', type=int, default=0, help='Minimum integer value (inclusive)')
    parser.add_argument('--max', dest='max_value', type=int, default=1_000_000_000, help='Maximum integer value (inclusive)')
    parser.add_argument('--per-line', dest='per_line', type=int, default=8, help='How many numbers to place on each line')
    parser.add_argument('--spike', dest='spike', type=float, default=0.02, help='Probability of emitting an extra-large spike value (0-1)')

    args = parser.parse_args()

    if args.size <= 0:
        print("❌ Error: Size must be a positive integer")
        return 1

    if args.files is not None and args.files <= 0:
        print("❌ Error: Number of files must be a positive integer")
        return 1

    if args.min_value >= args.max_value:
        print("❌ Error: --min must be smaller than --max")
        return 1

    if args.per_line <= 0:
        print("❌ Error: --per-line must be a positive integer")
        return 1

    if not 0 <= args.spike <= 1:
        print("❌ Error: --spike must be between 0 and 1")
        return 1

    generator = DatasetGenerator(
        min_value=args.min_value,
        max_value=args.max_value,
        numbers_per_line=args.per_line,
        spike_chance=args.spike
    )

    try:
        generator.generate_dataset(
            total_size_mb=args.size,
            output_dir=args.output,
            num_files=args.files,
            prefix=args.prefix
        )
        return 0
    except KeyboardInterrupt:
        print("\n❌ Generation interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error generating dataset: {e}")
        return 1


if __name__ == '__main__':
    main()
