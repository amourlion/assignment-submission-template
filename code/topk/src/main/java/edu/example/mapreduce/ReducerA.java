package edu.example.mapreduce;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.NullWritable;
import org.apache.hadoop.mapreduce.Reducer;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.PriorityQueue;

/**
 * Reducer (and combiner) merges mapper partial top-K results into the global top-K.
 */
public class ReducerA extends Reducer<NullWritable, LongWritable, LongWritable, NullWritable> {

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

        List<Long> result = new ArrayList<>(heap);
        result.sort(Collections.reverseOrder()); // Descending output

        LongWritable outKey = new LongWritable();
        for (Long num : result) {
            outKey.set(num);
            context.write(outKey, NullWritable.get());
        }
    }
}
