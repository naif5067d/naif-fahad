/**
 * Smart Rich Text Editor Component
 * Canva/Notion-like intelligent editor with RTL support
 */
import { useEditor, EditorContent, BubbleMenu } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Highlight from '@tiptap/extension-highlight';
import TextStyle from '@tiptap/extension-text-style';
import Color from '@tiptap/extension-color';
import Table from '@tiptap/extension-table';
import TableRow from '@tiptap/extension-table-row';
import TableHeader from '@tiptap/extension-table-header';
import TableCell from '@tiptap/extension-table-cell';
import Placeholder from '@tiptap/extension-placeholder';
import Typography from '@tiptap/extension-typography';
import { 
  Bold, Italic, Underline, List, ListOrdered, 
  Heading1, Heading2, Heading3, Quote, Minus, 
  Table as TableIcon, AlertTriangle, Info, 
  Palette, Highlighter, Undo, Redo
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { useLanguage } from '@/contexts/LanguageContext';

// Custom Warning/Notice block extension
import { Node, mergeAttributes } from '@tiptap/core';

const WarningBlock = Node.create({
  name: 'warningBlock',
  group: 'block',
  content: 'inline*',
  parseHTML() {
    return [{ tag: 'div[data-type="warning"]' }];
  },
  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes(HTMLAttributes, { 
      'data-type': 'warning',
      'class': 'warning-block p-4 my-4 rounded-lg border-r-4 border-amber-500 bg-amber-50 dark:bg-amber-950/30'
    }), 0];
  },
});

const NoticeBlock = Node.create({
  name: 'noticeBlock',
  group: 'block',
  content: 'inline*',
  parseHTML() {
    return [{ tag: 'div[data-type="notice"]' }];
  },
  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes(HTMLAttributes, { 
      'data-type': 'notice',
      'class': 'notice-block p-4 my-4 rounded-lg border-r-4 border-blue-500 bg-blue-50 dark:bg-blue-950/30'
    }), 0];
  },
});

const COLORS = [
  '#000000', '#434343', '#666666', '#999999', '#b7b7b7', '#cccccc',
  '#d9d9d9', '#efefef', '#f3f3f3', '#ffffff',
  '#980000', '#ff0000', '#ff9900', '#ffff00', '#00ff00', '#00ffff',
  '#4a86e8', '#0000ff', '#9900ff', '#ff00ff',
  '#e6b8af', '#f4cccc', '#fce5cd', '#fff2cc', '#d9ead3', '#d0e0e3',
  '#c9daf8', '#cfe2f3', '#d9d2e9', '#ead1dc',
];

const HIGHLIGHT_COLORS = [
  '#fef08a', '#bef264', '#6ee7b7', '#67e8f9', '#a5b4fc', '#f0abfc',
  '#fda4af', '#fed7aa', '#fde68a', '#d9f99d',
];

export default function SmartEditor({ 
  content = '', 
  onChange, 
  readOnly = false,
  placeholder = 'ابدأ الكتابة هنا...'
}) {
  const { lang } = useLanguage();
  const isRTL = lang === 'ar';

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: {
          levels: [1, 2, 3],
        },
      }),
      TextStyle,
      Color,
      Highlight.configure({ multicolor: true }),
      Table.configure({
        resizable: true,
        HTMLAttributes: {
          class: 'border-collapse border border-border my-4 w-full',
        },
      }),
      TableRow,
      TableHeader.configure({
        HTMLAttributes: {
          class: 'border border-border bg-muted p-2 font-bold',
        },
      }),
      TableCell.configure({
        HTMLAttributes: {
          class: 'border border-border p-2',
        },
      }),
      Typography,
      Placeholder.configure({
        placeholder,
      }),
      WarningBlock,
      NoticeBlock,
    ],
    content,
    editable: !readOnly,
    onUpdate: ({ editor }) => {
      if (onChange) {
        onChange(editor.getHTML());
      }
    },
    editorProps: {
      attributes: {
        class: `prose prose-sm sm:prose max-w-none focus:outline-none min-h-[300px] p-4 ${isRTL ? 'text-right' : 'text-left'}`,
        dir: isRTL ? 'rtl' : 'ltr',
      },
    },
  });

  if (!editor) {
    return null;
  }

  const ToolbarButton = ({ onClick, active, disabled, children, title }) => (
    <Button
      type="button"
      variant={active ? 'default' : 'ghost'}
      size="sm"
      onClick={onClick}
      disabled={disabled || readOnly}
      className="h-8 w-8 p-0"
      title={title}
    >
      {children}
    </Button>
  );

  const insertTable = () => {
    editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run();
  };

  const insertWarning = () => {
    editor.chain().focus().insertContent({
      type: 'warningBlock',
      content: [{ type: 'text', text: isRTL ? 'تحذير: ' : 'Warning: ' }]
    }).run();
  };

  const insertNotice = () => {
    editor.chain().focus().insertContent({
      type: 'noticeBlock',
      content: [{ type: 'text', text: isRTL ? 'ملاحظة: ' : 'Notice: ' }]
    }).run();
  };

  return (
    <div className={`smart-editor border rounded-lg overflow-hidden bg-background ${readOnly ? 'opacity-75' : ''}`} dir={isRTL ? 'rtl' : 'ltr'}>
      {/* Toolbar */}
      {!readOnly && (
        <div className="toolbar flex flex-wrap items-center gap-1 p-2 border-b bg-muted/30">
          {/* Undo/Redo */}
          <ToolbarButton
            onClick={() => editor.chain().focus().undo().run()}
            disabled={!editor.can().undo()}
            title="Undo"
          >
            <Undo size={16} />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().redo().run()}
            disabled={!editor.can().redo()}
            title="Redo"
          >
            <Redo size={16} />
          </ToolbarButton>

          <div className="w-px h-6 bg-border mx-1" />

          {/* Text formatting */}
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleBold().run()}
            active={editor.isActive('bold')}
            title="Bold (Ctrl+B)"
          >
            <Bold size={16} />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleItalic().run()}
            active={editor.isActive('italic')}
            title="Italic (Ctrl+I)"
          >
            <Italic size={16} />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleStrike().run()}
            active={editor.isActive('strike')}
            title="Strikethrough"
          >
            <Underline size={16} />
          </ToolbarButton>

          <div className="w-px h-6 bg-border mx-1" />

          {/* Headings */}
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
            active={editor.isActive('heading', { level: 1 })}
            title="Heading 1"
          >
            <Heading1 size={16} />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
            active={editor.isActive('heading', { level: 2 })}
            title="Heading 2"
          >
            <Heading2 size={16} />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
            active={editor.isActive('heading', { level: 3 })}
            title="Heading 3"
          >
            <Heading3 size={16} />
          </ToolbarButton>

          <div className="w-px h-6 bg-border mx-1" />

          {/* Lists */}
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleBulletList().run()}
            active={editor.isActive('bulletList')}
            title="Bullet List"
          >
            <List size={16} />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleOrderedList().run()}
            active={editor.isActive('orderedList')}
            title="Numbered List"
          >
            <ListOrdered size={16} />
          </ToolbarButton>

          <div className="w-px h-6 bg-border mx-1" />

          {/* Blockquote & Divider */}
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleBlockquote().run()}
            active={editor.isActive('blockquote')}
            title="Quote"
          >
            <Quote size={16} />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().setHorizontalRule().run()}
            title="Divider"
          >
            <Minus size={16} />
          </ToolbarButton>

          <div className="w-px h-6 bg-border mx-1" />

          {/* Table */}
          <ToolbarButton onClick={insertTable} title="Insert Table">
            <TableIcon size={16} />
          </ToolbarButton>

          <div className="w-px h-6 bg-border mx-1" />

          {/* Warning & Notice */}
          <ToolbarButton onClick={insertWarning} title={isRTL ? 'تحذير' : 'Warning Block'}>
            <AlertTriangle size={16} className="text-amber-500" />
          </ToolbarButton>
          <ToolbarButton onClick={insertNotice} title={isRTL ? 'ملاحظة' : 'Notice Block'}>
            <Info size={16} className="text-blue-500" />
          </ToolbarButton>

          <div className="w-px h-6 bg-border mx-1" />

          {/* Text Color */}
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="ghost" size="sm" className="h-8 w-8 p-0" title="Text Color">
                <Palette size={16} />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-64 p-2">
              <div className="grid grid-cols-10 gap-1">
                {COLORS.map((color) => (
                  <button
                    key={color}
                    className="w-5 h-5 rounded border border-border hover:scale-110 transition-transform"
                    style={{ backgroundColor: color }}
                    onClick={() => editor.chain().focus().setColor(color).run()}
                  />
                ))}
              </div>
            </PopoverContent>
          </Popover>

          {/* Highlight */}
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="ghost" size="sm" className="h-8 w-8 p-0" title="Highlight">
                <Highlighter size={16} />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-48 p-2">
              <div className="grid grid-cols-5 gap-1">
                {HIGHLIGHT_COLORS.map((color) => (
                  <button
                    key={color}
                    className="w-6 h-6 rounded border border-border hover:scale-110 transition-transform"
                    style={{ backgroundColor: color }}
                    onClick={() => editor.chain().focus().toggleHighlight({ color }).run()}
                  />
                ))}
              </div>
            </PopoverContent>
          </Popover>
        </div>
      )}

      {/* Bubble Menu for quick formatting */}
      {!readOnly && (
        <BubbleMenu editor={editor} tippyOptions={{ duration: 100 }}>
          <div className="flex items-center gap-1 p-1 rounded-lg border bg-background shadow-lg">
            <Button
              variant={editor.isActive('bold') ? 'default' : 'ghost'}
              size="sm"
              className="h-7 w-7 p-0"
              onClick={() => editor.chain().focus().toggleBold().run()}
            >
              <Bold size={14} />
            </Button>
            <Button
              variant={editor.isActive('italic') ? 'default' : 'ghost'}
              size="sm"
              className="h-7 w-7 p-0"
              onClick={() => editor.chain().focus().toggleItalic().run()}
            >
              <Italic size={14} />
            </Button>
            <Button
              variant={editor.isActive('highlight') ? 'default' : 'ghost'}
              size="sm"
              className="h-7 w-7 p-0"
              onClick={() => editor.chain().focus().toggleHighlight({ color: '#fef08a' }).run()}
            >
              <Highlighter size={14} />
            </Button>
          </div>
        </BubbleMenu>
      )}

      {/* Editor Content */}
      <EditorContent editor={editor} className="policy-editor-content" />

      {/* Editor Styles */}
      <style jsx global>{`
        .policy-editor-content .ProseMirror {
          min-height: 300px;
          outline: none;
        }
        .policy-editor-content .ProseMirror p.is-editor-empty:first-child::before {
          color: #9ca3af;
          content: attr(data-placeholder);
          float: left;
          height: 0;
          pointer-events: none;
        }
        .policy-editor-content .ProseMirror h1 {
          font-size: 1.875rem;
          font-weight: 700;
          margin-bottom: 0.75rem;
          font-family: 'Georgia', serif;
        }
        .policy-editor-content .ProseMirror h2 {
          font-size: 1.5rem;
          font-weight: 600;
          margin-bottom: 0.5rem;
          font-family: 'Georgia', serif;
        }
        .policy-editor-content .ProseMirror h3 {
          font-size: 1.25rem;
          font-weight: 600;
          margin-bottom: 0.5rem;
        }
        .policy-editor-content .ProseMirror blockquote {
          border-right: 4px solid hsl(var(--primary));
          padding-right: 1rem;
          margin: 1rem 0;
          font-style: italic;
          color: hsl(var(--muted-foreground));
        }
        [dir="ltr"] .policy-editor-content .ProseMirror blockquote {
          border-right: none;
          border-left: 4px solid hsl(var(--primary));
          padding-right: 0;
          padding-left: 1rem;
        }
        .policy-editor-content .ProseMirror hr {
          border: none;
          border-top: 2px solid hsl(var(--border));
          margin: 1.5rem 0;
        }
        .policy-editor-content .ProseMirror ul,
        .policy-editor-content .ProseMirror ol {
          padding-right: 1.5rem;
          margin: 0.5rem 0;
        }
        [dir="ltr"] .policy-editor-content .ProseMirror ul,
        [dir="ltr"] .policy-editor-content .ProseMirror ol {
          padding-right: 0;
          padding-left: 1.5rem;
        }
        .policy-editor-content .ProseMirror table {
          border-collapse: collapse;
          width: 100%;
          margin: 1rem 0;
        }
        .policy-editor-content .ProseMirror th,
        .policy-editor-content .ProseMirror td {
          border: 1px solid hsl(var(--border));
          padding: 0.5rem;
          text-align: right;
        }
        [dir="ltr"] .policy-editor-content .ProseMirror th,
        [dir="ltr"] .policy-editor-content .ProseMirror td {
          text-align: left;
        }
        .policy-editor-content .ProseMirror th {
          background: hsl(var(--muted));
          font-weight: 600;
        }
        .warning-block {
          background: rgb(254 243 199 / 0.3);
          border-right: 4px solid rgb(245 158 11);
          padding: 1rem;
          border-radius: 0.5rem;
          margin: 1rem 0;
        }
        [dir="ltr"] .warning-block {
          border-right: none;
          border-left: 4px solid rgb(245 158 11);
        }
        .notice-block {
          background: rgb(219 234 254 / 0.3);
          border-right: 4px solid rgb(59 130 246);
          padding: 1rem;
          border-radius: 0.5rem;
          margin: 1rem 0;
        }
        [dir="ltr"] .notice-block {
          border-right: none;
          border-left: 4px solid rgb(59 130 246);
        }
        .dark .warning-block {
          background: rgb(120 53 15 / 0.2);
        }
        .dark .notice-block {
          background: rgb(30 58 138 / 0.2);
        }
      `}</style>
    </div>
  );
}
