package edu.example.mapreduce;

import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.NullWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Mapper;

import java.io.IOException;

/**
 * Emits entire non-empty lines as keys so duplicates collapse at Reduce.
 */
public class DedupMapper extends Mapper<LongWritable, Text, Text, NullWritable> {

    private final Text reusableKey = new Text();

    @Override
    protected void map(LongWritable key, Text value, Context context)
            throws IOException, InterruptedException {

        String line = value.toString().trim();
        if (line.isEmpty()) {
            return;
        }
        reusableKey.set(line);
        context.write(reusableKey, NullWritable.get());
    }
}
