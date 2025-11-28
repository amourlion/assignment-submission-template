#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Universal Dataset Generator for Hadoop MapReduce Experiments
Generates text datasets of any size for word count analysis with realistic text patterns.
Usage: python3 generate_data.py <size_in_mb> [options]
"""

import os
import random
import string
import argparse
import sys
import bisect
from datetime import datetime

class DatasetGenerator:
    def __init__(
        self,
        profile="default",
        unique_keys=None,
        hotspot_ratio=0.0,
        hotspot_portion=0.2,
        zipf_s=1.2,
        long_id_rate=0.0,
    ):
        # Common English words for realistic text generation
        self.common_words = [
            'hadoop', 'mapreduce', 'yarn', 'hdfs', 'spark', 'kafka', 'storm', 'hive', 'pig', 'zookeeper',
            'distributed', 'computing', 'cluster', 'node', 'data', 'processing', 'analytics', 'streaming',
            'batch', 'real-time', 'big', 'scale', 'framework', 'apache', 'ecosystem', 'pipeline',
            'storage', 'compute', 'memory', 'disk', 'network', 'bandwidth', 'latency', 'throughput',
            'performance', 'optimization', 'tuning', 'configuration', 'monitoring', 'metrics', 'logging',
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from',
            'system', 'application', 'service', 'job', 'task', 'process', 'thread', 'queue', 'buffer',
            'algorithm', 'structure', 'pattern', 'design', 'architecture', 'implementation', 'solution',
            'problem', 'issue', 'error', 'exception', 'failure', 'success', 'result', 'output', 'input',
            'file', 'directory', 'path', 'location', 'resource', 'allocation', 'scheduling', 'execution',
            'parallel', 'concurrent', 'sequential', 'synchronous', 'asynchronous', 'blocking', 'non-blocking',
            'master', 'worker', 'client', 'server', 'manager', 'coordinator', 'controller', 'monitor',
            'startup', 'shutdown', 'restart', 'recovery', 'backup', 'restore', 'migration', 'upgrade',
            'version', 'release', 'build', 'deployment', 'production', 'development', 'testing', 'staging',
            'environment', 'container', 'virtual', 'machine', 'instance', 'image', 'snapshot', 'checkpoint'
        ]
        
        # Technical terms for variety
        self.tech_terms = [
            'slowstart', 'reducer', 'mapper', 'shuffle', 'combiner', 'partitioner', 'serialization',
            'compression', 'codec', 'format', 'schema', 'metadata', 'catalog', 'registry', 'repository',
            'warehouse', 'lake', 'mart', 'cube', 'dimension', 'measure', 'aggregation', 'transformation',
            'extraction', 'loading', 'cleaning', 'validation', 'enrichment', 'integration', 'synchronization',
            'replication', 'sharding', 'partitioning', 'bucketing', 'indexing', 'caching', 'memoization',
            'pagination', 'filtering', 'sorting', 'grouping', 'joining', 'union', 'intersection', 'difference'
        ]
        
        # Numbers and identifiers
        self.numbers = [str(i) for i in range(0, 1000, 5)]
        self.hex_chars = '0123456789abcdef'
        
        # Distribution configuration
        self.profile = profile
        self.unique_keys = unique_keys
        self.hotspot_ratio = hotspot_ratio
        self.hotspot_portion = hotspot_portion
        self.zipf_s = zipf_s
        self.long_id_rate = long_id_rate
        self.show_progress = True
        
        # Vocabulary cache (used when profile != default)
        self.vocab = None
        self.vocab_weights = None
        self.cum_weights = None
    
    def _make_random_token(self, long_form=False):
        """Create a random token; optionally generate longer IDs"""
        if long_form:
            length = random.randint(16, 40)
        else:
            length = random.randint(4, 12)
        if random.random() < 0.5:
            return ''.join(random.choices(self.hex_chars, k=length))
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    
    def _prepare_vocabulary(self):
        """Build vocabulary and weights for custom profiles"""
        # Base vocab comes from existing word pools
        base_vocab = list(dict.fromkeys(self.common_words + self.tech_terms))
        
        # Expand to desired unique size if requested
        if self.unique_keys and self.unique_keys > len(base_vocab):
            needed = self.unique_keys - len(base_vocab)
            for _ in range(needed):
                base_vocab.append(self._make_random_token(long_form=random.random() < self.long_id_rate))
            # Deduplicate while keeping order
            base_vocab = list(dict.fromkeys(base_vocab))
        
        # If no special profile is set, leave vocab None to use legacy logic
        if self.profile == "default":
            return
        
        # Uniform weights
        weights = [1.0] * len(base_vocab)
        
        if self.profile == "hotspot" and self.hotspot_ratio > 0:
            # Pick hotspot words and boost their weights
            hotspot_count = max(1, min(len(base_vocab), int(len(base_vocab) * self.hotspot_portion)))
            hotspot_words = set(random.sample(base_vocab, hotspot_count))
            boosted = self.hotspot_ratio
            weights = [boosted if w in hotspot_words else 1.0 for w in base_vocab]
        elif self.profile == "zipf":
            # Zipf-like weighting based on rank
            ranks = list(range(1, len(base_vocab) + 1))
            random.shuffle(ranks)  # avoid deterministic top words; keep randomness
            weights = [1.0 / (r ** self.zipf_s) for r in ranks]
        elif self.profile == "longid":
            # Increase chance of long IDs in the vocab sampling
            extra = int(len(base_vocab) * max(0.1, self.long_id_rate or 0.2))
            for _ in range(extra):
                base_vocab.append(self._make_random_token(long_form=True))
            weights = [1.0] * len(base_vocab)
        
        self.vocab = base_vocab
        self.vocab_weights = weights
        
        # Precompute cumulative weights for fast sampling when needed
        if self.profile in ("hotspot", "zipf", "longid"):
            total = 0.0
            self.cum_weights = []
            for w in self.vocab_weights:
                total += w
                self.cum_weights.append(total)
    
    def _print_progress_bar(self, percent):
        """Render a lightweight progress bar in-place"""
        if not self.show_progress:
            return
        bar_len = 40
        filled = int(bar_len * percent / 100)
        bar = '#' * filled + '-' * (bar_len - filled)
        sys.stdout.write(f"\r  [{bar}] {percent:5.1f}%")
        sys.stdout.flush()
        if percent >= 100:
            sys.stdout.write("\n")
    
    def generate_word(self):
        """Generate a single word with weighted probability"""
        # If a custom vocabulary is prepared, sample from it directly
        if self.vocab:
            # Uniform sampling over vocab without weights (fast path)
            if self.profile == "uniform":
                return random.choice(self.vocab)
            
            # Weighted sampling using precomputed cumulative weights
            if self.cum_weights:
                r = random.random() * self.cum_weights[-1]
                idx = bisect.bisect_left(self.cum_weights, r)
                return self.vocab[idx]
            
            # Fallback (should not hit)
            return random.choice(self.vocab)
        
        rand = random.random()
        if rand < 0.6:  # 60% common words
            return random.choice(self.common_words)
        elif rand < 0.8:  # 20% tech terms
            return random.choice(self.tech_terms)
        elif rand < 0.9:  # 10% numbers
            return random.choice(self.numbers)
        else:  # 10% random strings (simulating IDs, hashes, etc.)
            return self._make_random_token(long_form=self.long_id_rate > 0 and random.random() < self.long_id_rate)
    
    def generate_line(self, min_words=5, max_words=20):
        """Generate a line of text with random number of words"""
        word_count = random.randint(min_words, max_words)
        words = [self.generate_word() for _ in range(word_count)]
        return ' '.join(words)
    
    def generate_structured_content(self, lines_per_block=100):
        """Generate structured content with some patterns for better MapReduce testing"""
        content = []
        
        # Add some repeated patterns for interesting reduce operations
        patterns = [
            "hadoop cluster node-{} status: active",
            "mapreduce job job_{} mapper task-{} completed",
            "yarn application app_{} resource allocation: {} MB memory",
            "hdfs block blk_{} replicated on datanode-{}",
            "spark executor executor-{} task-{} processing partition-{}"
        ]
        
        for _ in range(lines_per_block):
            if random.random() < 0.3:  # 30% structured patterns
                pattern = random.choice(patterns)
                if '{}' in pattern:
                    # Fill in random numbers for placeholders
                    args = [random.randint(1, 999) for _ in range(pattern.count('{}'))]
                    line = pattern.format(*args)
                else:
                    line = pattern
            else:  # 70% random content
                line = self.generate_line()
            
            content.append(line)
        
        return content
    
    def generate_file(self, filepath, target_size_mb, progress_callback=None):
        """Generate a single file with specified size"""
        target_size_bytes = target_size_mb * 1024 * 1024
        current_size = 0
        lines_written = 0
        last_bar = -1.0
        
        with open(filepath, 'w', encoding='utf-8') as f:
            while current_size < target_size_bytes:
                # Generate content in blocks for better performance
                content_lines = self.generate_structured_content()
                
                for line in content_lines:
                    f.write(line + '\n')
                    current_size += len(line.encode('utf-8')) + 1  # +1 for newline
                    lines_written += 1
                    
                    # Update simple progress bar every ~50k lines
                    if self.show_progress and lines_written % 50000 == 0:
                        progress_pct = min(100, (current_size / target_size_bytes) * 100)
                        if abs(progress_pct - last_bar) >= 1.0:
                            self._print_progress_bar(progress_pct)
                            last_bar = progress_pct
                    
                    if current_size >= target_size_bytes:
                        break
                
                # Progress reporting
                if progress_callback and lines_written % 1000000 == 0:
                    progress_pct = min(100, (current_size / target_size_bytes) * 100)
                    progress_callback(filepath, progress_pct, current_size, lines_written)
        
        # Finalize progress bar
        if self.show_progress:
            self._print_progress_bar(100)
        
        return current_size, lines_written
    
    def calculate_optimal_files(self, total_size_mb):
        """Calculate optimal number of files based on dataset size"""
        if total_size_mb <= 5:
            return 2  # Small datasets: 2 files
        elif total_size_mb <= 50:
            return 4  # Medium datasets: 4 files
        elif total_size_mb <= 500:
            return 8  # Large datasets: 8 files
        else:
            return max(16, min(32, total_size_mb // 100))  # Very large: 16-32 files
    
    def generate_dataset(self, total_size_mb, output_dir=None, num_files=None, prefix='data'):
        """Generate complete dataset with multiple files"""
        # Build vocabulary when custom profiles are requested
        self._prepare_vocabulary()
        
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
        
        print(f"=== Generating {total_size_mb}MB dataset ===")
        print(f"Output directory: {output_dir}")
        print(f"Number of files: {num_files}")
        print(f"Target size per file: {size_per_file_mb:.2f}MB")
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        total_bytes = 0
        total_lines = 0
        start_time = datetime.now()
        
        def progress_callback(filepath, progress_pct, current_size, lines_written):
            print(f"  {os.path.basename(filepath)}: {progress_pct:.1f}% ({current_size/1024/1024:.1f}MB, {lines_written:,} lines)")
        
        for i in range(num_files):
            filename = f"{prefix}{i+1:02d}.txt"
            filepath = os.path.join(output_dir, filename)
            
            print(f"\nGenerating file {i+1}/{num_files}: {filename}")
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
        print(f"Average speed: {(total_bytes/1024/1024)/duration:.2f} MB/s")
        
        # Generate upload script for HDFS
        self.create_hdfs_upload_script(output_dir, num_files, prefix)
        
        return output_dir, total_bytes, total_lines
    
    def create_hdfs_upload_script(self, output_dir, num_files, prefix):
        """Create HDFS upload script (files with replication factor = 1)"""
        upload_script_path = os.path.join(output_dir, 'upload_to_hdfs.sh')
        
        # Determine default HDFS path based on output directory
        if 'local' in output_dir:
            default_hdfs_path = '/mr_input_local'
        elif 'small' in output_dir:
            default_hdfs_path = '/mr_input_small'
        else:
            default_hdfs_path = '/mr_input'
        
        with open(upload_script_path, 'w') as f:
            f.write('#!/bin/bash\n\n')
            f.write('# Upload generated dataset to HDFS with replication = 1\n')
            f.write('# Usage: ./upload_to_hdfs.sh [hdfs_path] [replication]\n')
            f.write('#   hdfs_path   : HDFS target directory (default: '
                    f'{default_hdfs_path})\n')
            f.write('#   replication : replication factor (default: 1)\n\n')
            
            # 参数 1：HDFS 目标路径；参数 2：复制系数，默认 1
            f.write(f'HDFS_PATH=${{1:-"{default_hdfs_path}"}}\n')
            f.write('REPLICATION=${2:-1}\n\n')
            
            f.write('echo "Creating HDFS directory: $HDFS_PATH"\n')
            f.write('hdfs dfs -mkdir -p "$HDFS_PATH"\n\n')
            
            f.write('echo "Uploading dataset files with replication = $REPLICATION ..."\n')
            for i in range(num_files):
                filename = f"{prefix}{i+1:02d}.txt"
                # 这里用 -Ddfs.replication=$REPLICATION 控制单文件复制系数
                f.write(
                    'hdfs dfs -Ddfs.replication="$REPLICATION" '
                    f'-put -f "{filename}" "$HDFS_PATH/"\n'
                )
            
            # 兜底：上传完再统一 setrep 一遍，保证目录下所有文件都是该复制系数
            f.write('\necho "Ensuring replication factor = $REPLICATION on $HDFS_PATH ..."\n')
            f.write('hdfs dfs -setrep -w "$REPLICATION" "$HDFS_PATH"\n\n')
            
            f.write('echo "Upload completed. Verifying..."\n')
            f.write('hdfs dfs -ls "$HDFS_PATH"\n')
            f.write('hdfs dfs -du -h "$HDFS_PATH"\n')
        
        os.chmod(upload_script_path, 0o755)
        
        print(f"\n📝 Additional files created:")
        print(f"  - HDFS upload script: {upload_script_path}")
        print(f"\n🚀 Next steps:")
        print(f"  1. Upload to HDFS: cd {output_dir} && ./upload_to_hdfs.sh {default_hdfs_path} 1")
        print(f"  2. Run experiments: ./monitor_job.sh 0.3 {default_hdfs_path} /mr_output")

def main():
    parser = argparse.ArgumentParser(
        description='Generate datasets of any size for Hadoop MapReduce experiments',
        epilog="""
Examples:
  python3 generate_data.py 1           # Generate 1MB dataset
  python3 generate_data.py 100         # Generate 100MB dataset  
  python3 generate_data.py 1000        # Generate 1GB dataset
  python3 generate_data.py 50 --files 8 --output my-data --prefix test
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('size', type=int, help='Dataset size in MB')
    parser.add_argument('--files', type=int, help='Number of files to generate (auto-calculated if not specified)')
    parser.add_argument('--output', type=str, help='Output directory (auto-determined if not specified)')
    parser.add_argument('--prefix', type=str, default='data', help='File prefix (default: data)')
    parser.add_argument('--profile', type=str, default='default',
                        choices=['default', 'uniform', 'hotspot', 'zipf', 'longid'],
                        help='Token distribution profile')
    parser.add_argument('--unique-keys', type=int, default=None,
                        help='Approximate number of unique tokens to sample from (extends vocab)')
    parser.add_argument('--hotspot-ratio', type=float, default=0.0,
                        help='Weight boost for hotspot words when profile=hotspot (e.g., 5.0)')
    parser.add_argument('--hotspot-portion', type=float, default=0.2,
                        help='Portion of vocab treated as hotspots when profile=hotspot (0-1)')
    parser.add_argument('--zipf-s', type=float, default=1.2,
                        help='Zipf exponent when profile=zipf (higher = more skew)')
    parser.add_argument('--long-id-rate', type=float, default=0.0,
                        help='Probability to emit longer ID-like tokens (0-1)')
    parser.add_argument('--no-progress', action='store_true',
                        help='Disable progress bar output')
    
    args = parser.parse_args()
    
    # Validate input
    if args.size <= 0:
        print("❌ Error: Size must be a positive integer")
        return 1
    
    if args.files is not None and args.files <= 0:
        print("❌ Error: Number of files must be a positive integer")
        return 1
    
    generator = DatasetGenerator(
        profile=args.profile,
        unique_keys=args.unique_keys,
        hotspot_ratio=args.hotspot_ratio,
        hotspot_portion=args.hotspot_portion,
        zipf_s=args.zipf_s,
        long_id_rate=args.long_id_rate,
    )
    generator.show_progress = not args.no_progress
    
    try:
        output_dir, total_bytes, total_lines = generator.generate_dataset(
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
