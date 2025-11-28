package edu.example.mapreduce;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.NullWritable;
import org.apache.hadoop.mapreduce.Reducer;

import java.io.IOException;
import java.util.PriorityQueue;

/**
 * Combiner merges mapper partial top-K results; output types must match map output.
 */
public class CombinerA extends Reducer<NullWritable, LongWritable, NullWritable, LongWritable> {

    private int topK;

    @Override
    protected void setup(Context context) throws IOException, InterruptedException {
        Configuration conf = context.getConfiguration();
        this.topK = Math.max(1, conf.getInt("top.k", 10));
    }

    @Override
    protected void reduce(NullWritable key, Iterable<LongWritable> values, Context context)
            throws IOException, InterruptedException {

        PriorityQueue<Long> heap = new PriorityQueue<>(topK); // min-heap

        for (LongWritable v : values) {
            long number = v.get();
            if (heap.size() < topK) {
                heap.add(number);
            } else if (number > heap.peek()) {
                heap.poll();
                heap.add(number);
            }
        }

        LongWritable outValue = new LongWritable();
        for (Long num : heap) {
            outValue.set(num);
            context.write(NullWritable.get(), outValue);
        }
    }
}
