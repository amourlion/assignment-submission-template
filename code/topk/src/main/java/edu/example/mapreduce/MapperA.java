package edu.example.mapreduce;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.NullWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Mapper;

import java.io.IOException;
import java.util.PriorityQueue;

/**
 * Mapper keeps a local top-K of the largest numbers it sees and emits only those.
 */
public class MapperA extends Mapper<LongWritable, Text, NullWritable, LongWritable> {

    private PriorityQueue<Long> topKHeap;
    private int topK;

    @Override
    protected void setup(Context context) throws IOException, InterruptedException {
        Configuration conf = context.getConfiguration();
        this.topK = Math.max(1, conf.getInt("top.k", 10));
        this.topKHeap = new PriorityQueue<>(topK); // min-heap
    }

    @Override
    protected void map(LongWritable key, Text value, Context context)
            throws IOException, InterruptedException {

        String[] tokens = value.toString().trim().split("\\s+");
        for (String token : tokens) {
            if (token.isEmpty()) {
                continue;
            }
            try {
                long number = Long.parseLong(token);
                addToTopK(number);
            } catch (NumberFormatException ignore) {
                // Skip tokens that are not valid integers
            }
        }
    }

    private void addToTopK(long number) {
        if (topKHeap.size() < topK) {
            topKHeap.add(number);
        } else if (number > topKHeap.peek()) {
            topKHeap.poll();
            topKHeap.add(number);
        }
    }

    @Override
    protected void cleanup(Context context) throws IOException, InterruptedException {
        LongWritable outValue = new LongWritable();
        for (Long num : topKHeap) {
            outValue.set(num);
            context.write(NullWritable.get(), outValue);
        }
    }
}
