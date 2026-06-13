import { zodResolver } from "@hookform/resolvers/zod";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useForm } from "react-hook-form";
import { describe, expect, it } from "vitest";
import { z } from "zod";

import { Input } from "./input";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "./form";

const schema = z.object({ name: z.string().min(1, "Project name is required") });

function Example() {
  const form = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: { name: "" },
  });
  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(() => {})}>
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Project name</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <button type="submit">Submit</button>
      </form>
    </Form>
  );
}

describe("Form", () => {
  it("surfaces the validation message on invalid submit", async () => {
    render(<Example />);
    await userEvent.click(screen.getByText("Submit"));
    expect(await screen.findByText("Project name is required")).toBeTruthy();
  });

  it("wires the label to the control and marks it invalid (a11y)", async () => {
    render(<Example />);
    await userEvent.click(screen.getByText("Submit"));
    const input = await screen.findByLabelText("Project name");
    expect(input.getAttribute("aria-invalid")).toBe("true");
  });
});
